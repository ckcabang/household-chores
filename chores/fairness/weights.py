"""Fairness-weight defaults, bounds, and the plain params object.

Framework-agnostic, like the rest of ``chores.fairness``: this module imports
nothing from Django. ``chores.models.FairnessWeights`` stores a household's
values and imports the constants below so the stored defaults and the pure
functions can never disagree; the workload code (tasks #13, #14) reads a
:class:`FairnessParams` the caller builds from those stored values.

Meaning of each value
---------------------
``time_weight``
    Multiplies a chore's estimated minutes. ``1.0`` counts time
    minute-for-minute; ``0.5`` halves the influence of raw time.
``difficulty_weight``
    How far difficulty swings a chore's workload around the "Moderate"
    baseline. ``1.0`` lets a "Very hard" chore count for 1.5x its minutes and a
    "Very easy" one for 0.5x (see :func:`chores.fairness.workload_value`);
    ``0.0`` ignores difficulty entirely.
``decay_half_life_days``
    Age, in days, at which a past contribution counts for half. Older history
    fades smoothly rather than dropping off a cliff (task #13).
"""

from __future__ import annotations

from dataclasses import dataclass

# Documented defaults. A brand-new household starts perfectly neutral: time
# counted as-is, difficulty swinging one full factor either way, and a month
# for contributions to decay to half.
DEFAULT_TIME_WEIGHT = 1.0
DEFAULT_DIFFICULTY_WEIGHT = 1.0
DEFAULT_DECAY_HALF_LIFE_DAYS = 30

# Allowed ranges, enforced on both the model and the edit form. The weights are
# non-negative and capped so a single slider can't dwarf the other factor
# entirely; the half-life must be a positive number of days.
WEIGHT_MIN = 0.0
WEIGHT_MAX = 5.0
HALF_LIFE_MIN_DAYS = 1


@dataclass(frozen=True)
class FairnessParams:
    """A household's fairness weights as a plain, immutable value object.

    Structurally compatible with the ``weights`` argument of
    :func:`chores.fairness.workload_value` (it reads ``time_weight`` and
    ``difficulty_weight``) and additionally carries ``decay_half_life_days``
    for the decayed-workload function.
    """

    time_weight: float = DEFAULT_TIME_WEIGHT
    difficulty_weight: float = DEFAULT_DIFFICULTY_WEIGHT
    decay_half_life_days: int = DEFAULT_DECAY_HALF_LIFE_DAYS


def weight_errors(
    time_weight: float,
    difficulty_weight: float,
    decay_half_life_days: int,
) -> dict[str, str]:
    """Return ``{field: message}`` for any value outside its allowed range.

    Empty dict means the values are valid. Shared by the model's ``clean`` and
    the form so the two cannot drift apart.
    """
    errors: dict[str, str] = {}
    for field, value in (
        ("time_weight", time_weight),
        ("difficulty_weight", difficulty_weight),
    ):
        if value is None or not (WEIGHT_MIN <= value <= WEIGHT_MAX):
            errors[field] = (
                f"Must be between {WEIGHT_MIN} and {WEIGHT_MAX}."
            )
    if decay_half_life_days is None or decay_half_life_days < HALF_LIFE_MIN_DAYS:
        errors["decay_half_life_days"] = (
            f"Must be at least {HALF_LIFE_MIN_DAYS} day."
        )
    return errors
