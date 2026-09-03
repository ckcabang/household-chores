"""Unit tests for chores.fairness.member_workloads - pure, no database."""

from datetime import datetime, timedelta, timezone

import pytest

from chores.fairness import (
    FairnessParams,
    WorkItem,
    decay_factor,
    member_workloads,
    who_is_ahead,
    workload_value,
)

NOW = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
PARAMS = FairnessParams()  # neutral: time 1.0, difficulty 1.0, half-life 30d

ALICE, BOB = 1, 2


def item(days_ago, *, actor, owner, minutes=30, effort=3, credited=False):
    return WorkItem(
        actor_id=actor,
        owner_id=owner,
        timestamp=NOW - timedelta(days=days_ago),
        minutes=minutes,
        effort=effort,
        credited=credited,
    )


# --- basics -------------------------------------------------------


def test_empty_input_maps_every_member_to_zero():
    assert member_workloads([], [ALICE, BOB], PARAMS, NOW) == {ALICE: 0.0, BOB: 0.0}


def test_one_fresh_completion_lands_fully_on_the_owner():
    result = member_workloads(
        [item(0, actor=ALICE, owner=ALICE, minutes=30, effort=3)],
        [ALICE, BOB],
        PARAMS,
        NOW,
    )
    assert result[ALICE] == pytest.approx(30.0)
    assert result[BOB] == 0.0


def test_two_members_with_matching_fresh_work_are_balanced():
    result = member_workloads(
        [
            item(0, actor=ALICE, owner=ALICE),
            item(0, actor=BOB, owner=BOB),
        ],
        [ALICE, BOB],
        PARAMS,
        NOW,
    )
    assert result[ALICE] == pytest.approx(result[BOB])


def test_precomputed_value_overrides_minutes_and_effort():
    result = member_workloads(
        [
            WorkItem(
                actor_id=ALICE, owner_id=ALICE, timestamp=NOW, value=12.5,
                minutes=999, effort=1,
            )
        ],
        [ALICE, BOB],
        PARAMS,
        NOW,
    )
    assert result[ALICE] == pytest.approx(12.5)


# --- decay ------------------------------------------------------


@pytest.mark.parametrize(
    ("half_lives", "expected_factor"),
    [(0, 1.0), (1, 0.5), (2, 0.25)],
)
def test_decay_at_zero_one_two_half_lives(half_lives, expected_factor):
    half_life = PARAMS.decay_half_life_days
    result = member_workloads(
        [item(half_lives * half_life, actor=ALICE, owner=ALICE, minutes=40, effort=3)],
        [ALICE, BOB],
        PARAMS,
        NOW,
    )
    assert result[ALICE] == pytest.approx(40.0 * expected_factor)


def test_decay_factor_helper_matches_formula():
    assert decay_factor(0, 30) == 1.0
    assert decay_factor(30, 30) == pytest.approx(0.5)
    assert decay_factor(60, 30) == pytest.approx(0.25)


# --- contribution credit --------------------------------------


def test_credited_completion_moves_workload_to_the_helper():
    # Bob owns the chore; Alice did it and holds the credit.
    result = member_workloads(
        [item(0, actor=ALICE, owner=BOB, minutes=30, effort=3, credited=True)],
        [ALICE, BOB],
        PARAMS,
        NOW,
    )
    assert result[ALICE] == pytest.approx(30.0)
    assert result[BOB] == 0.0


def test_uncredited_completion_by_non_owner_still_lands_on_the_owner():
    result = member_workloads(
        [item(0, actor=ALICE, owner=BOB, credited=False)],
        [ALICE, BOB],
        PARAMS,
        NOW,
    )
    assert result[BOB] == pytest.approx(30.0)
    assert result[ALICE] == 0.0


def test_ownerless_chore_lands_on_the_actor():
    result = member_workloads(
        [item(0, actor=ALICE, owner=None)],
        [ALICE, BOB],
        PARAMS,
        NOW,
    )
    assert result[ALICE] == pytest.approx(30.0)


def test_work_for_an_unknown_member_is_ignored():
    result = member_workloads(
        [item(0, actor=99, owner=99)],
        [ALICE, BOB],
        PARAMS,
        NOW,
    )
    assert result == {ALICE: 0.0, BOB: 0.0}


# --- weights flow through -------------------------------------


def test_params_feed_the_workload_formula():
    heavy = FairnessParams(time_weight=2.0, difficulty_weight=1.0, decay_half_life_days=30)
    result = member_workloads(
        [item(0, actor=ALICE, owner=ALICE, minutes=30, effort=3)],
        [ALICE, BOB],
        heavy,
        NOW,
    )
    assert result[ALICE] == pytest.approx(workload_value(30, 3, heavy))
    assert result[ALICE] == pytest.approx(60.0)


# --- who_is_ahead --------------------------------------------


def test_who_is_ahead_picks_the_heavier_member():
    assert who_is_ahead({ALICE: 10.0, BOB: 4.0}) == ALICE


def test_who_is_ahead_returns_none_on_a_tie():
    assert who_is_ahead({ALICE: 5.0, BOB: 5.0}) is None
    assert who_is_ahead({}) is None
