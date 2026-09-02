"""The single per-item workload derivation used across the fairness code.

This module is deliberately framework-agnostic: it imports nothing from
``django`` or ``chores.models`` so it can be unit-tested without Django
settings or a database. Capture (task #11), weighting (#12) and workload
with decay (#13) all route their per-item arithmetic through
:func:`workload_value` so the definition cannot drift.

Formula
-------
Given a chore's rough time estimate ``estimated_minutes`` and its
``difficulty`` on the 1..5 scale (3 = "Moderate" is the neutral baseline)::

    BASELINE_DIFFICULTY = 3
    DIFFICULTY_MIN, DIFFICULTY_MAX = 1, 5

    w = weights or WorkloadWeights()
    difficulty_factor = 1.0 + w.difficulty_weight * (
        (difficulty - BASELINE_DIFFICULTY) / (DIFFICULTY_MAX - DIFFICULTY_MIN)
    )
    return w.time_weight * estimated_minutes * difficulty_factor

A "Moderate" chore is worth exactly its estimated minutes; harder chores
scale up and easier ones down, linearly, by up to one difficulty_weight in
either direction.

Worked examples with the neutral default weights::

    workload_value(30, 3) == 30.0
    workload_value(30, 5) == 45.0
    workload_value(20, 1) == 10.0
"""

from __future__ import annotations

from dataclasses import dataclass

# The difficulty scale, defined locally so this package never imports Django.
# ``chores.models.DIFFICULTY_MIN`` / ``DIFFICULTY_MAX`` and the "Moderate"
# label in ``DIFFICULTY_CHOICES`` are the authoritative source; a test in
# ``chores/tests/`` asserts these copies match so the two cannot drift.
BASELINE_DIFFICULTY = 3
DIFFICULTY_MIN = 1
DIFFICULTY_MAX = 5


@dataclass(frozen=True)
class WorkloadWeights:
    """How much time and difficulty each count toward a chore's workload.

    Both default to ``1.0``, which is the neutral setting: time is counted
    minute-for-minute and difficulty swings the value by up to one full
    factor either side of the "Moderate" baseline. Task #12 adapts a
    household's stored ``FairnessWeights`` into this shape; until then the
    completion path uses these defaults.
    """

    time_weight: float = 1.0
    difficulty_weight: float = 1.0


def workload_value(
    estimated_minutes: int,
    difficulty: int,
    weights: WorkloadWeights | None = None,
) -> float:
    """Return the workload a single chore occurrence is worth.

    See the module docstring for the formula and worked examples.
    """
    w = weights or WorkloadWeights()
    difficulty_factor = 1.0 + w.difficulty_weight * (
        (difficulty - BASELINE_DIFFICULTY) / (DIFFICULTY_MAX - DIFFICULTY_MIN)
    )
    return w.time_weight * estimated_minutes * difficulty_factor
