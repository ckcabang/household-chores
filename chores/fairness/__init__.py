"""Framework-agnostic fairness logic.

Importing this package must not touch Django settings or the ORM. Keep every
module here free of ``django.*`` and ``chores.models`` imports.
"""

from .assignment import (
    AssignableChore,
    AssignmentResult,
    ChoreProposal,
    propose_assignments,
)
from .balance import (
    WorkItem,
    decay_factor,
    member_workloads,
    who_is_ahead,
)
from .estimates import (
    ESTIMATE_CHANGE_THRESHOLD,
    ESTIMATE_MIN_SAMPLES,
    ESTIMATE_SAMPLE_SIZE,
    EstimateSuggestion,
    propose_estimate,
)
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
    "AssignableChore",
    "AssignmentResult",
    "BASELINE_DIFFICULTY",
    "ChoreProposal",
    "ESTIMATE_CHANGE_THRESHOLD",
    "ESTIMATE_MIN_SAMPLES",
    "ESTIMATE_SAMPLE_SIZE",
    "EstimateSuggestion",
    "DEFAULT_DECAY_HALF_LIFE_DAYS",
    "DEFAULT_DIFFICULTY_WEIGHT",
    "DEFAULT_TIME_WEIGHT",
    "DIFFICULTY_MAX",
    "DIFFICULTY_MIN",
    "FairnessParams",
    "HALF_LIFE_MIN_DAYS",
    "WEIGHT_MAX",
    "WEIGHT_MIN",
    "WorkItem",
    "WorkloadWeights",
    "decay_factor",
    "member_workloads",
    "propose_assignments",
    "propose_estimate",
    "weight_errors",
    "who_is_ahead",
    "workload_value",
]
