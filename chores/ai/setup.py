"""Generate a draft household chore plan with the Anthropic API.

The only module that imports ``anthropic``. ``generate_plan`` builds the
request, asks for structured output via a single forced tool call, validates
the result against the expected shape, and returns a :class:`ParsedPlan` - or
raises one of the errors below. The client is injectable; when it is not
supplied one is built from ``ANTHROPIC_API_KEY``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

# Structured-output model. Overridable via the ANTHROPIC_MODEL env var; the
# default follows the current claude-api guidance.
DEFAULT_MODEL = "claude-opus-5"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_TOKENS = 4096

# The household is permanently two people (see _docs/plan.md).
HOUSEHOLD_SIZE = 2

DIFFICULTY_MIN = 1
DIFFICULTY_MAX = 5

SYSTEM_PROMPT = (
    "You help a two-person household set up a fair chore plan. Given their "
    "answers and description, propose a realistic set of recurring chores with "
    "cadences and time/difficulty estimates, any preferences or exclusions you "
    "can infer between a person and a chore, an initial assignment of each "
    "chore to one of the two members, and a short plain-language explanation of "
    "your reasoning. Always answer by calling the submit_household_plan tool."
)

PLAN_TOOL = {
    "name": "submit_household_plan",
    "description": "Submit the proposed chore plan for the household.",
    "input_schema": {
        "type": "object",
        "properties": {
            "chores": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "cadence_days": {"type": "integer", "minimum": 1},
                        "estimated_minutes": {"type": "integer", "minimum": 1},
                        "difficulty": {
                            "type": "integer",
                            "minimum": DIFFICULTY_MIN,
                            "maximum": DIFFICULTY_MAX,
                        },
                    },
                    "required": [
                        "name",
                        "cadence_days",
                        "estimated_minutes",
                        "difficulty",
                    ],
                },
            },
            "constraints": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "person": {"type": "string"},
                        "chore": {"type": "string"},
                        "kind": {"type": "string", "enum": ["prefer", "exclude"]},
                    },
                    "required": ["person", "chore", "kind"],
                },
            },
            "assignments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "chore": {"type": "string"},
                        "member": {"type": "string"},
                    },
                    "required": ["chore", "member"],
                },
            },
            "reasoning": {"type": "string"},
        },
        "required": ["chores", "constraints", "assignments", "reasoning"],
    },
}


class AISetupError(Exception):
    """Base class for every AI-setup failure."""


class AISetupConfigError(AISetupError):
    """The API key (or other configuration) is missing."""


class PlanGenerationError(AISetupError):
    """The API call failed - network error, timeout, 4xx or 5xx."""


class PlanValidationError(AISetupError):
    """The model's response did not match the expected plan shape."""


@dataclass
class ParsedPlan:
    chores: list[dict] = field(default_factory=list)
    constraints: list[dict] = field(default_factory=list)
    assignments: list[dict] = field(default_factory=list)
    reasoning: str = ""
    raw: dict = field(default_factory=dict)


def build_client(api_key: str | None = None, timeout: float = DEFAULT_TIMEOUT_SECONDS):
    """Return a real Anthropic client, or raise :class:`AISetupConfigError`."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise AISetupConfigError(
            "ANTHROPIC_API_KEY is not set - AI setup is unavailable."
        )
    import anthropic  # imported lazily so the app boots without the key

    return anthropic.Anthropic(api_key=key, timeout=timeout)


def _build_user_prompt(answers: dict, description: str) -> str:
    lines = [f"Household size: {HOUSEHOLD_SIZE} (fixed)."]
    for key, value in answers.items():
        label = key.replace("_", " ").capitalize()
        lines.append(f"{label}: {value}")
    lines.append("")
    lines.append("Free-form description:")
    lines.append(description.strip() or "(none provided)")
    return "\n".join(lines)


def _block_attr(block: Any, name: str):
    if isinstance(block, dict):
        return block.get(name)
    return getattr(block, name, None)


def _extract_plan_input(response: Any) -> dict:
    content = _block_attr(response, "content") or []
    for block in content:
        if _block_attr(block, "type") == "tool_use":
            data = _block_attr(block, "input")
            if isinstance(data, dict):
                return data
    raise PlanValidationError("The model did not return a structured plan.")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PlanValidationError(message)


def _validate_plan(data: dict) -> None:
    _require(isinstance(data, dict), "Plan is not an object.")

    chores = data.get("chores")
    _require(
        isinstance(chores, list) and len(chores) > 0,
        "Plan has no chores.",
    )
    for chore in chores:
        _require(isinstance(chore, dict), "A chore entry is not an object.")
        _require(
            isinstance(chore.get("name"), str) and chore["name"].strip() != "",
            "A chore is missing a name.",
        )
        for numeric in ("cadence_days", "estimated_minutes"):
            _require(
                isinstance(chore.get(numeric), int) and chore[numeric] >= 1,
                f"A chore has an invalid {numeric}.",
            )
        difficulty = chore.get("difficulty")
        _require(
            isinstance(difficulty, int)
            and DIFFICULTY_MIN <= difficulty <= DIFFICULTY_MAX,
            "A chore has an out-of-range difficulty.",
        )

    constraints = data.get("constraints", [])
    _require(isinstance(constraints, list), "Constraints is not a list.")
    for constraint in constraints:
        _require(isinstance(constraint, dict), "A constraint is not an object.")
        _require(
            isinstance(constraint.get("person"), str)
            and isinstance(constraint.get("chore"), str)
            and constraint.get("kind") in ("prefer", "exclude"),
            "A constraint entry is malformed.",
        )

    assignments = data.get("assignments", [])
    _require(isinstance(assignments, list), "Assignments is not a list.")
    for assignment in assignments:
        _require(
            isinstance(assignment, dict)
            and isinstance(assignment.get("chore"), str)
            and isinstance(assignment.get("member"), str),
            "An assignment entry is malformed.",
        )

    _require(isinstance(data.get("reasoning"), str), "Plan is missing reasoning.")


def generate_plan(
    answers: dict,
    description: str,
    *,
    client: Any | None = None,
    model: str | None = None,
) -> ParsedPlan:
    """Ask the model for a household plan and return it parsed and validated.

    Raises :class:`AISetupConfigError` (no key), :class:`PlanGenerationError`
    (API/transport failure) or :class:`PlanValidationError` (bad shape).
    """
    if client is None:
        client = build_client()
    model = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL

    try:
        response = client.messages.create(
            model=model,
            max_tokens=DEFAULT_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": _build_user_prompt(answers, description),
                }
            ],
            tools=[PLAN_TOOL],
            tool_choice={"type": "tool", "name": PLAN_TOOL["name"]},
        )
    except AISetupError:
        raise
    except Exception as exc:  # anthropic.APIError, transport errors, etc.
        raise PlanGenerationError(str(exc)) from exc

    plan = _extract_plan_input(response)
    _validate_plan(plan)
    return ParsedPlan(
        chores=plan["chores"],
        constraints=plan.get("constraints", []),
        assignments=plan.get("assignments", []),
        reasoning=plan["reasoning"],
        raw=plan,
    )
