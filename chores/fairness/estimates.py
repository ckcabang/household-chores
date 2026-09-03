"""Compare logged actual times against a chore's estimate and, past a
threshold, suggest a new estimate.

Framework-agnostic, like the rest of ``chores.fairness``. The app layer
gathers a chore's ``Completion.actual_minutes`` values and this module decides
whether a change is worth proposing; persistence (the ``EstimateProposal``
model) lives in ``chores/models.py``.

Tunables
--------
``ESTIMATE_SAMPLE_SIZE``
    Only the most recent N logged actual times are considered.
``ESTIMATE_MIN_SAMPLES``
    Fewer than this many logged times -> no proposal (not enough signal).
``ESTIMATE_CHANGE_THRESHOLD``
    The median of the sample must differ from the current estimate by more
    than this fraction (0.25 = 25%) before a change is proposed.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Sequence

ESTIMATE_SAMPLE_SIZE = 5
ESTIMATE_MIN_SAMPLES = 3
ESTIMATE_CHANGE_THRESHOLD = 0.25


@dataclass(frozen=True)
class EstimateSuggestion:
    proposed_minutes: int
    rationale: str


def propose_estimate(
    current_minutes: int,
    actual_minutes: Sequence[int | None],
) -> EstimateSuggestion | None:
    """Return a suggested new estimate, or ``None`` to leave the estimate alone.

    ``actual_minutes`` is in chronological order (oldest first); ``None`` entries
    (no time logged) are skipped and the most recent
    ``ESTIMATE_SAMPLE_SIZE`` real values are used.
    """
    samples = [m for m in actual_minutes if m is not None][-ESTIMATE_SAMPLE_SIZE:]
    if len(samples) < ESTIMATE_MIN_SAMPLES or current_minutes <= 0:
        return None

    typical = median(samples)
    relative_change = abs(typical - current_minutes) / current_minutes
    if relative_change <= ESTIMATE_CHANGE_THRESHOLD:
        return None

    proposed = max(1, round(typical))
    direction = "longer" if proposed > current_minutes else "shorter"
    return EstimateSuggestion(
        proposed_minutes=proposed,
        rationale=(
            f"The last {len(samples)} logged times have a median of "
            f"{typical:g} min, {round(relative_change * 100)}% {direction} than "
            f"the current {current_minutes} min estimate."
        ),
    )
