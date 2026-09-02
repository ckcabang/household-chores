"""Framework-agnostic fairness logic.

Importing this package must not touch Django settings or the ORM. Keep every
module here free of ``django.*`` and ``chores.models`` imports.
"""

from .workload import (
    BASELINE_DIFFICULTY,
    DIFFICULTY_MAX,
    DIFFICULTY_MIN,
    WorkloadWeights,
    workload_value,
)

__all__ = [
    "BASELINE_DIFFICULTY",
    "DIFFICULTY_MAX",
    "DIFFICULTY_MIN",
    "WorkloadWeights",
    "workload_value",
]
