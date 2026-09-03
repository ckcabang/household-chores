"""Framework-agnostic fairness logic.

Importing this package must not touch Django settings or the ORM. Keep every
module here free of ``django.*`` and ``chores.models`` imports.
"""

from .weights import (
    DEFAULT_DECAY_HALF_LIFE_DAYS,
    DEFAULT_DIFFICULTY_WEIGHT,
    DEFAULT_TIME_WEIGHT,
    HALF_LIFE_MIN_DAYS,
    WEIGHT_MAX,
    WEIGHT_MIN,
    FairnessParams,
    weight_errors,
)
from .workload import (
    BASELINE_DIFFICULTY,
    DIFFICULTY_MAX,
    DIFFICULTY_MIN,
    WorkloadWeights,
    workload_value,
)

__all__ = [
    "BASELINE_DIFFICULTY",
    "DEFAULT_DECAY_HALF_LIFE_DAYS",
    "DEFAULT_DIFFICULTY_WEIGHT",
    "DEFAULT_TIME_WEIGHT",
    "DIFFICULTY_MAX",
    "DIFFICULTY_MIN",
    "FairnessParams",
    "HALF_LIFE_MIN_DAYS",
    "WEIGHT_MAX",
    "WEIGHT_MIN",
    "WorkloadWeights",
    "weight_errors",
    "workload_value",
]
