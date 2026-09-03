"""Estimate-learning: the pure comparison, the generator, accept/dismiss."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from chores.fairness import propose_estimate
from chores.models import (
    Chore,
    ChoreOccurrence,
    Completion,
    EstimateProposal,
    Household,
    Membership,
    OCCURRENCE_STATUS_COMPLETED,
    PROPOSAL_STATUS_ACCEPTED,
    PROPOSAL_STATUS_DISMISSED,
    PROPOSAL_STATUS_PENDING,
)
from chores.proposals import generate_estimate_proposals

User = get_user_model()
PW = "correct-horse-7"


# --- pure function -------------------------------------------------


def test_no_proposal_below_the_minimum_sample_count():
    assert propose_estimate(30, [60, 60]) is None


def test_no_proposal_when_within_threshold():
    # median 33 vs 30 -> 10% < 25%
    assert propose_estimate(30, [30, 33, 36]) is None


def test_proposal_when_actuals_run_long():
    suggestion = propose_estimate(30, [50, 55, 60])
    assert suggestion is not None
    assert suggestion.proposed_minutes == 55
    assert "longer" in suggestion.rationale


def test_proposal_when_actuals_run_short():
    suggestion = propose_estimate(60, [30, 30, 35])
    assert suggestion is not None
    assert suggestion.proposed_minutes == 30
    assert "shorter" in suggestion.rationale


def test_only_the_most_recent_samples_count():
    # Old huge values, five recent ~20s -> should propose ~20, not be dragged up.
    suggestion = propose_estimate(60, [999, 999, 20, 21, 19, 20, 22])
    assert suggestion.proposed_minutes == pytest.approx(20, abs=1)


def test_none_entries_are_skipped():
    assert propose_estimate(30, [None, None, 30]) is None
    assert propose_estimate(30, [None, 60, 62, 58]) is not None


# --- fixtures for the DB-backed tests --------------------------


@pytest.fixture
def nest(db):
    return Household.objects.create(name="The Nest")


@pytest.fixture
def alice_m(nest):
    u = User.objects.create_user(username="alice", password=PW)
    return Membership.objects.create(user=u, household=nest)


@pytest.fixture
def signed_in_alice(client, alice_m):
    client.login(username="alice", password=PW)
    return alice_m


def chore_with_actuals(nest, actuals, *, name="Dishes", estimate=30):
    chore = Chore.objects.create(
        household=nest,
        name=name,
        cadence_days=3,
        estimated_minutes=estimate,
        difficulty=3,
    )
    base = timezone.now() - timedelta(days=len(actuals) + 1)
    for i, minutes in enumerate(actuals):
        occ = ChoreOccurrence.objects.create(
            chore=chore,
            due_date=(base + timedelta(days=i)).date(),
            status=OCCURRENCE_STATUS_COMPLETED,
            completed_at=base + timedelta(days=i),
        )
        Completion.objects.create(
            occurrence=occ,
            completed_by=chore.household.memberships.first(),
            actual_minutes=minutes,
        )
    return chore


# --- generator ---------------------------------------------------


@pytest.mark.django_db
def test_generator_creates_a_pending_proposal_past_threshold(nest, alice_m):
    chore = chore_with_actuals(nest, [55, 58, 60])
    created = generate_estimate_proposals(nest)
    assert len(created) == 1
    assert created[0].chore == chore
    assert created[0].status == PROPOSAL_STATUS_PENDING


@pytest.mark.django_db
def test_generator_makes_no_proposal_within_threshold(nest, alice_m):
    chore_with_actuals(nest, [30, 31, 29])
    assert generate_estimate_proposals(nest) == []


@pytest.mark.django_db
def test_generator_does_not_duplicate_a_pending_proposal(nest, alice_m):
    chore_with_actuals(nest, [55, 58, 60])
    generate_estimate_proposals(nest)
    generate_estimate_proposals(nest)
    assert EstimateProposal.objects.filter(status=PROPOSAL_STATUS_PENDING).count() == 1


# --- accept / dismiss ------------------------------------------


@pytest.mark.django_db
def test_accept_updates_the_chore_and_marks_accepted(client, signed_in_alice, nest):
    chore = chore_with_actuals(nest, [55, 58, 60])
    proposal = generate_estimate_proposals(nest)[0]

    response = client.post(
        reverse("chores:estimate_proposal_accept", args=[proposal.pk])
    )
    assert response.status_code == 302

    chore.refresh_from_db()
    proposal.refresh_from_db()
    assert chore.estimated_minutes == proposal.proposed_minutes
    assert proposal.status == PROPOSAL_STATUS_ACCEPTED
    assert proposal.decided_by == signed_in_alice
    assert proposal.decided_at is not None


@pytest.mark.django_db
def test_dismiss_leaves_the_chore_unchanged(client, signed_in_alice, nest):
    chore = chore_with_actuals(nest, [55, 58, 60])
    original = chore.estimated_minutes
    proposal = generate_estimate_proposals(nest)[0]

    client.post(reverse("chores:estimate_proposal_dismiss", args=[proposal.pk]))

    chore.refresh_from_db()
    proposal.refresh_from_db()
    assert chore.estimated_minutes == original
    assert proposal.status == PROPOSAL_STATUS_DISMISSED


@pytest.mark.django_db
def test_deciding_an_already_decided_proposal_is_a_noop(client, signed_in_alice, nest):
    chore = chore_with_actuals(nest, [55, 58, 60])
    proposal = generate_estimate_proposals(nest)[0]
    client.post(reverse("chores:estimate_proposal_dismiss", args=[proposal.pk]))

    response = client.post(
        reverse("chores:estimate_proposal_accept", args=[proposal.pk]), follow=True
    )
    proposal.refresh_from_db()
    chore.refresh_from_db()
    assert proposal.status == PROPOSAL_STATUS_DISMISSED
    assert chore.estimated_minutes == 30
    assert any("already been decided" in str(m) for m in response.context["messages"])


@pytest.mark.django_db
def test_cross_household_proposal_is_404(client, signed_in_alice, nest):
    other = Household.objects.create(name="Next door")
    Membership.objects.create(
        user=User.objects.create_user(username="carol", password=PW),
        household=other,
    )
    their_chore = chore_with_actuals(other, [55, 58, 60], name="Theirs")
    proposal = generate_estimate_proposals(other)[0]

    response = client.post(
        reverse("chores:estimate_proposal_accept", args=[proposal.pk])
    )
    assert response.status_code == 404
    their_chore.refresh_from_db()
    assert their_chore.estimated_minutes == 30


@pytest.mark.django_db
def test_refresh_button_runs_the_generator(client, signed_in_alice, nest):
    chore_with_actuals(nest, [55, 58, 60])
    response = client.post(
        reverse("chores:estimate_proposal_refresh"), follow=True
    )
    assert EstimateProposal.objects.filter(status=PROPOSAL_STATUS_PENDING).count() == 1
    assert any("suggest a new estimate" in str(m) for m in response.context["messages"])


@pytest.mark.django_db
def test_list_shows_pending_proposals(client, signed_in_alice, nest):
    chore_with_actuals(nest, [55, 58, 60], name="Vacuuming")
    generate_estimate_proposals(nest)
    body = client.get(reverse("chores:estimate_proposal_list")).content.decode()
    assert "Vacuuming" in body
