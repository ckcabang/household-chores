"""Unit tests for chores.fairness.propose_assignments - pure, no database."""

import pytest

from chores.fairness import AssignableChore, propose_assignments

ALICE, BOB = 1, 2


def owners(result):
    return {p.chore_id: p.proposed_owner_id for p in result.proposals}


# --- balance ----------------------------------------------------


def test_all_chores_go_to_the_idle_member():
    chores = [AssignableChore(id=10, cost=30.0), AssignableChore(id=11, cost=20.0)]
    result = propose_assignments(chores, {ALICE: 0.0, BOB: 100.0})
    assert owners(result) == {10: ALICE, 11: ALICE}
    assert result.projected[ALICE] == pytest.approx(50.0)
    assert result.projected[BOB] == pytest.approx(100.0)


def test_greedy_by_decreasing_cost_splits_two_chores():
    chores = [AssignableChore(id=10, cost=30.0), AssignableChore(id=11, cost=25.0)]
    result = propose_assignments(chores, {ALICE: 0.0, BOB: 0.0})
    # Biggest chore to the lower id, next chore to the now-lighter member.
    assert owners(result) == {10: ALICE, 11: BOB}


def test_result_is_deterministic_for_the_same_input():
    chores = [AssignableChore(id=i, cost=float(i)) for i in range(5)]
    a = propose_assignments(chores, {ALICE: 3.0, BOB: 1.0})
    b = propose_assignments(chores, {ALICE: 3.0, BOB: 1.0})
    assert owners(a) == owners(b)
    assert a.projected == b.projected


def test_empty_input_returns_no_proposals():
    result = propose_assignments([], {ALICE: 0.0, BOB: 0.0})
    assert result.proposals == []
    assert result.projected == {ALICE: 0.0, BOB: 0.0}


# --- constraints ---------------------------------------------


def test_exclusion_forces_the_other_member():
    chores = [AssignableChore(id=10, cost=30.0)]
    # Alice is lighter but excluded from chore 10.
    result = propose_assignments(
        chores, {ALICE: 0.0, BOB: 50.0}, [(ALICE, 10, "exclude")]
    )
    assert owners(result) == {10: BOB}


def test_both_members_excluded_makes_the_chore_unassignable():
    chores = [AssignableChore(id=10, cost=30.0)]
    result = propose_assignments(
        chores,
        {ALICE: 0.0, BOB: 0.0},
        [(ALICE, 10, "exclude"), (BOB, 10, "exclude")],
    )
    proposal = result.proposals[0]
    assert proposal.unassignable is True
    assert proposal.proposed_owner_id is None
    # Nobody's projected workload moved.
    assert result.projected == {ALICE: 0.0, BOB: 0.0}


def test_preference_breaks_a_tie():
    chores = [AssignableChore(id=10, cost=30.0)]
    # Equal workload; Bob prefers the chore, so the tie breaks to Bob
    # instead of to the lower id (Alice).
    result = propose_assignments(
        chores, {ALICE: 0.0, BOB: 0.0}, [(BOB, 10, "prefer")]
    )
    assert owners(result) == {10: BOB}


def test_preference_does_not_override_balance():
    chores = [AssignableChore(id=10, cost=30.0)]
    # Alice prefers it but is far heavier; balance still wins.
    result = propose_assignments(
        chores, {ALICE: 100.0, BOB: 0.0}, [(ALICE, 10, "prefer")]
    )
    assert owners(result) == {10: BOB}


def test_tie_without_preference_breaks_to_lower_id():
    chores = [AssignableChore(id=10, cost=30.0)]
    result = propose_assignments(chores, {ALICE: 0.0, BOB: 0.0})
    assert owners(result) == {10: ALICE}


def test_current_owner_is_carried_onto_the_proposal():
    chores = [AssignableChore(id=10, cost=30.0, owner_id=BOB)]
    result = propose_assignments(chores, {ALICE: 0.0, BOB: 0.0})
    assert result.proposals[0].current_owner_id == BOB
