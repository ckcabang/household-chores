"""Weight-change proposals: creation, dual approval, rejection, the open-limit."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from chores.models import (
    FairnessWeights,
    Household,
    Membership,
    WEIGHT_PROPOSAL_STATUS_APPLIED,
    WEIGHT_PROPOSAL_STATUS_OPEN,
    WEIGHT_PROPOSAL_STATUS_REJECTED,
    WeightProposal,
)

User = get_user_model()
PW = "correct-horse-7"


@pytest.fixture
def nest(db):
    return Household.objects.create(name="The Nest")


@pytest.fixture
def alice_m(nest):
    u = User.objects.create_user(username="alice", password=PW)
    return Membership.objects.create(user=u, household=nest)


@pytest.fixture
def bob_m(nest):
    u = User.objects.create_user(username="bob", password=PW)
    return Membership.objects.create(user=u, household=nest)


@pytest.fixture
def as_alice(client, alice_m):
    client.login(username="alice", password=PW)
    return alice_m


@pytest.fixture
def as_bob(client, bob_m):
    client.login(username="bob", password=PW)
    return bob_m


NEW_VALUES = {
    "time_weight": "0.5",
    "difficulty_weight": "2.0",
    "decay_half_life_days": "45",
}


def create_url():
    return reverse("chores:weight_proposal_create")


# --- creation --------------------------------------------------


@pytest.mark.django_db
def test_create_records_the_creator_as_approving(client, as_alice, bob_m, nest):
    response = client.post(create_url(), NEW_VALUES)
    proposal = WeightProposal.objects.get()
    assert proposal.status == WEIGHT_PROPOSAL_STATUS_OPEN
    assert list(proposal.approved_by.all()) == [as_alice]
    assert not proposal.is_fully_approved()
    assert response.status_code == 302
    # Weights are untouched until both approve.
    weights = FairnessWeights.objects.get(household=nest)
    assert weights.time_weight == 1.0


@pytest.mark.django_db
def test_create_form_is_prefilled_with_current_values(client, as_alice, nest):
    body = client.get(create_url()).content.decode()
    assert 'value="1.0"' in body or 'value="1"' in body


@pytest.mark.django_db
def test_invalid_values_create_no_proposal(client, as_alice, nest):
    bad = {**NEW_VALUES, "decay_half_life_days": "0"}
    response = client.post(create_url(), bad)
    assert response.status_code == 200
    assert not WeightProposal.objects.exists()


# --- approval applies -----------------------------------------


@pytest.mark.django_db
def test_second_approval_applies_the_values(client, as_alice, bob_m, nest):
    client.post(create_url(), NEW_VALUES)
    proposal = WeightProposal.objects.get()

    client.logout()
    client.login(username="bob", password=PW)
    client.post(reverse("chores:weight_proposal_approve", args=[proposal.pk]))

    proposal.refresh_from_db()
    assert proposal.status == WEIGHT_PROPOSAL_STATUS_APPLIED
    assert proposal.resolved_at is not None

    weights = FairnessWeights.objects.get(household=nest)
    assert weights.time_weight == 0.5
    assert weights.difficulty_weight == 2.0
    assert weights.decay_half_life_days == 45


@pytest.mark.django_db
def test_rejection_leaves_weights_untouched(client, as_alice, bob_m, nest):
    client.post(create_url(), NEW_VALUES)
    proposal = WeightProposal.objects.get()

    client.logout()
    client.login(username="bob", password=PW)
    client.post(reverse("chores:weight_proposal_reject", args=[proposal.pk]))

    proposal.refresh_from_db()
    assert proposal.status == WEIGHT_PROPOSAL_STATUS_REJECTED
    weights = FairnessWeights.objects.get(household=nest)
    assert weights.time_weight == 1.0


# --- single open proposal -----------------------------------


@pytest.mark.django_db
def test_only_one_open_proposal_at_a_time(client, as_alice, bob_m, nest):
    client.post(create_url(), NEW_VALUES)
    first = WeightProposal.objects.get()

    response = client.post(create_url(), NEW_VALUES, follow=True)
    assert WeightProposal.objects.count() == 1
    assert response.redirect_chain[-1][0] == reverse(
        "chores:weight_proposal_detail", args=[first.pk]
    )
    assert any("already an open" in str(m) for m in response.context["messages"])


@pytest.mark.django_db
def test_a_new_proposal_is_allowed_after_the_previous_one_closes(
    client, as_alice, bob_m, nest
):
    client.post(create_url(), NEW_VALUES)
    proposal = WeightProposal.objects.get()
    proposal.reject()

    client.post(create_url(), NEW_VALUES)
    assert WeightProposal.objects.filter(status=WEIGHT_PROPOSAL_STATUS_OPEN).count() == 1


# --- no-op on a closed proposal ----------------------------


@pytest.mark.django_db
def test_approving_a_closed_proposal_is_a_noop(client, as_alice, bob_m, nest):
    client.post(create_url(), NEW_VALUES)
    proposal = WeightProposal.objects.get()
    proposal.reject()

    response = client.post(
        reverse("chores:weight_proposal_approve", args=[proposal.pk]), follow=True
    )
    proposal.refresh_from_db()
    assert proposal.status == WEIGHT_PROPOSAL_STATUS_REJECTED
    assert any("already closed" in str(m) for m in response.context["messages"])


# --- detail + scoping --------------------------------------


@pytest.mark.django_db
def test_detail_shows_proposed_and_current_and_approvals(client, as_alice, bob_m, nest):
    client.post(create_url(), NEW_VALUES)
    proposal = WeightProposal.objects.get()
    body = client.get(
        reverse("chores:weight_proposal_detail", args=[proposal.pk])
    ).content.decode()
    assert "0.5" in body  # proposed
    assert "alice: approved" in body
    assert "bob: not yet" in body


@pytest.mark.django_db
def test_other_household_proposal_is_404(client, as_alice):
    other = Household.objects.create(name="Next door")
    om = Membership.objects.create(
        user=User.objects.create_user(username="carol", password=PW),
        household=other,
    )
    proposal = WeightProposal.objects.create(household=other, created_by=om)
    response = client.get(
        reverse("chores:weight_proposal_detail", args=[proposal.pk])
    )
    assert response.status_code == 404
