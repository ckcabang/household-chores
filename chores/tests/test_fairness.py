"""Unit tests for the framework-agnostic ``chores.fairness`` package.

These run without a database and must not need Django settings.
"""

import os
import subprocess
import sys

import pytest

from chores.fairness import (
    BASELINE_DIFFICULTY,
    DIFFICULTY_MAX,
    DIFFICULTY_MIN,
    WorkloadWeights,
    workload_value,
)


# --- worked examples with the neutral default weights ----------------


@pytest.mark.parametrize(
    ("estimated_minutes", "difficulty", "expected"),
    [
        (30, 3, 30.0),
        (30, 5, 45.0),
        (20, 1, 10.0),
        (30, 4, 37.5),
        (30, 2, 22.5),
    ],
)
def test_workload_value_default_weights(estimated_minutes, difficulty, expected):
    assert workload_value(estimated_minutes, difficulty) == expected


def test_workload_value_none_weights_matches_default_instance():
    assert workload_value(40, 5, weights=None) == workload_value(
        40, 5, weights=WorkloadWeights()
    )


# --- explicit WorkloadWeights ---------------------------------------


def test_workload_weights_defaults_are_neutral():
    w = WorkloadWeights()
    assert w.time_weight == 1.0
    assert w.difficulty_weight == 1.0


def test_workload_weights_is_frozen():
    w = WorkloadWeights()
    with pytest.raises(Exception):
        w.time_weight = 2.0


def test_workload_value_with_explicit_weights():
    # difficulty_weight 0 removes the difficulty swing entirely.
    flat = WorkloadWeights(time_weight=1.0, difficulty_weight=0.0)
    assert workload_value(30, 5, weights=flat) == 30.0

    # time_weight scales the whole result linearly.
    doubled = WorkloadWeights(time_weight=2.0, difficulty_weight=1.0)
    assert workload_value(30, 5, weights=doubled) == 90.0

    # A heavier difficulty_weight widens the swing.
    steep = WorkloadWeights(time_weight=1.0, difficulty_weight=2.0)
    assert workload_value(20, 1, weights=steep) == 0.0


# --- drift guard against chores.models -----------------------------


def test_local_difficulty_bounds_match_chores_models():
    from chores.models import DIFFICULTY_CHOICES, DIFFICULTY_MIN as MODEL_MIN
    from chores.models import DIFFICULTY_MAX as MODEL_MAX

    assert DIFFICULTY_MIN == MODEL_MIN
    assert DIFFICULTY_MAX == MODEL_MAX

    moderate_value = next(
        value for value, label in DIFFICULTY_CHOICES if label == "Moderate"
    )
    assert BASELINE_DIFFICULTY == moderate_value


# --- no Django settings access on import --------------------------


def test_importing_chores_fairness_does_not_access_django_settings():
    """A subprocess with a bogus settings module still imports the package."""
    code = "\n".join(
        [
            "import chores.fairness",
            "from chores.fairness import workload_value",
            "assert workload_value(30, 3) == 30.0",
            "from django.conf import settings",
            "assert not settings.configured, 'fairness import configured settings'",
            # Nothing has configured Django and DJANGO_SETTINGS_MODULE points at a
            # module that does not exist, so touching any setting must fail.
            "try:",
            "    settings.DEBUG",
            "except Exception:",
            "    pass",
            "else:",
            "    raise AssertionError('Django settings were unexpectedly available')",
        ]
    )
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.does_not_exist"}
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        cwd=os.getcwd(),
    )
    assert result.returncode == 0, result.stderr
