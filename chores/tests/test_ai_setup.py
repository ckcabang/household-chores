"""AI setup plan generation: the isolated Anthropic module + the /setup/ view.

No network: every test injects a fake client or monkeypatches generate_plan.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from chores.ai import setup as ai_setup
from chores.ai.setup import (
    AISetupConfigError,
    ParsedPlan,
    PlanGenerationError,
    PlanValidationError,
    generate_plan,
)
from chores.models import AISetupDraft, Chore, Constraint, Household, Membership

User = get_user_model()
PW = "correct-horse-7"


VALID_PLAN = {
    "chores": [
        {"name": "Dishes", "cadence_days": 1, "estimated_minutes": 15, "difficulty": 2},
        {"name": "Vacuum", "cadence_days": 7, "estimated_minutes": 30, "difficulty": 3},
    ],
    "constraints": [
        {"person": "alice", "chore": "Dishes", "kind": "prefer"},
    ],
    "assignments": [
        {"chore": "Dishes", "member": "alice"},
        {"chore": "Vacuum", "member": "bob"},
    ],
    "reasoning": "Alice prefers dishes; the rest is split evenly.",
}


# --- fake Anthropic client ---------------------------------------


class _Block:
    def __init__(self, type_, data=None):
        self.type = type_
        self.input = data


class _Response:
    def __init__(self, blocks):
        self.content = blocks


class _Messages:
    def __init__(self, outer):
        self._outer = outer

    def create(self, **kwargs):
        self._outer.calls.append(kwargs)
        if self._outer.error is not None:
            raise self._outer.error
        return _Response(self._outer.blocks)


class FakeClient:
    def __init__(self, *, blocks=None, error=None):
        self.blocks = blocks if blocks is not None else [_Block("tool_use", VALID_PLAN)]
        self.error = error
        self.calls = []
        self.messages = _Messages(self)


# --- generate_plan ---------------------------------------------


def test_valid_response_is_parsed():
    client = FakeClient()
    plan = generate_plan({"home_type": "house"}, "We have a garden.", client=client)

    assert isinstance(plan, ParsedPlan)
    assert [c["name"] for c in plan.chores] == ["Dishes", "Vacuum"]
    assert plan.constraints[0]["kind"] == "prefer"
    assert plan.reasoning.startswith("Alice prefers")
    assert plan.raw == VALID_PLAN

    # It forces the structured-output tool call.
    (call,) = client.calls
    assert call["tool_choice"] == {"type": "tool", "name": "submit_household_plan"}
    assert call["model"]


def test_model_override_is_passed_through():
    client = FakeClient()
    generate_plan({}, "desc", client=client, model="claude-sonnet-5")
    assert client.calls[0]["model"] == "claude-sonnet-5"


def test_schema_invalid_response_raises_validation_error():
    bad = {**VALID_PLAN, "chores": []}
    client = FakeClient(blocks=[_Block("tool_use", bad)])
    with pytest.raises(PlanValidationError):
        generate_plan({}, "desc", client=client)


def test_missing_tool_use_block_raises_validation_error():
    client = FakeClient(blocks=[_Block("text")])
    with pytest.raises(PlanValidationError):
        generate_plan({}, "desc", client=client)


def test_chore_with_bad_types_raises_validation_error():
    bad = {
        **VALID_PLAN,
        "chores": [
            {"name": "X", "cadence_days": "weekly", "estimated_minutes": 10, "difficulty": 3}
        ],
    }
    client = FakeClient(blocks=[_Block("tool_use", bad)])
    with pytest.raises(PlanValidationError):
        generate_plan({}, "desc", client=client)


def test_api_error_becomes_plan_generation_error():
    client = FakeClient(error=RuntimeError("503 upstream"))
    with pytest.raises(PlanGenerationError):
        generate_plan({}, "desc", client=client)


def test_build_client_without_key_raises_config_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(AISetupConfigError):
        ai_setup.build_client()


def test_generate_plan_without_client_or_key_raises_config_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(AISetupConfigError):
        generate_plan({}, "desc")


# --- the /setup/ view ----------------------------------------


@pytest.fixture
def nest(db):
    return Household.objects.create(name="The Nest")


@pytest.fixture
def as_alice(client, nest):
    u = User.objects.create_user(username="alice", password=PW)
    Membership.objects.create(user=u, household=nest)
    client.login(username="alice", password=PW)
    return u


@pytest.fixture
def setup_url():
    return reverse("chores:setup")


FORM_DATA = {
    "home_type": "house",
    "rooms": "5",
    "description": "Two of us, one dog, we both work from home.",
}


@pytest.mark.django_db
def test_get_renders_the_questionnaire(client, as_alice, setup_url):
    body = client.get(setup_url).content.decode()
    assert 'name="description"' in body
    assert 'name="home_type"' in body


@pytest.mark.django_db
def test_anonymous_is_redirected_to_login(client, setup_url):
    response = client.get(setup_url)
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_valid_submit_saves_a_draft_and_creates_no_records(
    client, as_alice, nest, setup_url, monkeypatch
):
    monkeypatch.setattr(
        ai_setup,
        "generate_plan",
        lambda answers, description, **kw: ParsedPlan(
            chores=VALID_PLAN["chores"],
            constraints=VALID_PLAN["constraints"],
            assignments=VALID_PLAN["assignments"],
            reasoning=VALID_PLAN["reasoning"],
            raw=VALID_PLAN,
        ),
    )

    response = client.post(setup_url, FORM_DATA, follow=True)
    assert any("Draft plan generated" in str(m) for m in response.context["messages"])

    draft = AISetupDraft.objects.get()
    assert draft.household == nest
    assert draft.status == "draft"
    assert len(draft.chores) == 2
    assert Chore.objects.count() == 0
    assert Constraint.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("error", "needle"),
    [
        (PlanValidationError("bad"), "didn't match"),
        (AISetupConfigError("no key"), "isn't configured"),
        (PlanGenerationError("boom"), "Couldn't reach"),
    ],
)
def test_generation_failures_show_a_friendly_message_and_no_draft(
    client, as_alice, setup_url, monkeypatch, error, needle
):
    def boom(*args, **kwargs):
        raise error

    monkeypatch.setattr(ai_setup, "generate_plan", boom)

    response = client.post(setup_url, FORM_DATA)
    assert response.status_code == 200
    assert not AISetupDraft.objects.exists()
    assert any(needle in str(m) for m in response.context["messages"])


@pytest.mark.django_db
def test_blank_description_is_a_form_error(client, as_alice, setup_url, monkeypatch):
    monkeypatch.setattr(
        ai_setup, "generate_plan", lambda *a, **k: pytest.fail("called")
    )
    response = client.post(setup_url, {**FORM_DATA, "description": "   "})
    assert response.status_code == 200
    assert not AISetupDraft.objects.exists()
