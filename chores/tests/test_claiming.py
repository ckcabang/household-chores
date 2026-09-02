"""Claiming an occurrence and the helper-credit row a covered completion writes."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from chores.fairness import workload_value
from chores.models import (
    Chore,
    ChoreOccurrence,
    Completion,
    ContributionCredit,
    Household,
    Membership,
    OCCURRENCE_STATUS_ACTIVE,
    OCCURRENCE_STATUS_COMPLETED,
)

User = get_user_model()

GOOD_PASSWORD = "correct-horse-7"


# --- fixtures --------------------------------------------------------


@pytest.fixture
def list_url():
    return reverse("chores:occurrence_list")


@pytest.fixture
def nest(db):
    return Household.objects.create(name="The Nest")


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="alice", password=GOOD_PASSWORD)


@pytest.fixture
def bob(db):
    return User.objects.create_user(username="bob", password=GOOD_PASSWORD)


@pytest.fixture
def alice_m(alice, nest):
    return Membership.objects.create(user=alice, household=nest)


@pytest.fixture
def bob_m(bob, nest):
    return Membership.objects.create(user=bob, household=nest)


@pytest.fixture
def signed_in_alice(client, alice, alice_m):
    client.login(username="alice", password=GOOD_PASSWORD)
    return alice


@pytest.fixture
def other_household(db):
    house = Household.objects.create(name="Next door")
    carol = User.objects.create_user(username="carol", password=GOOD_PASSWORD)
    Membership.objects.create(user=carol, household=house)
    return house


def make_chore(household, *, name="Dishes", owner=None, minutes=15, difficulty=3):
    return Chore.objects.create(
        household=household,
        name=name,
        cadence_days=2,
        estimated_minutes=minutes,
        difficulty=difficulty,
        primary_owner=owner,
    )


def make_occurrence(chore, *, due_offset_days=0, status=OCCURRENCE_STATUS_ACTIVE):
    return ChoreOccurrence.objects.create(
        chore=chore,
        due_date=timezone.localdate() + timedelta(days=due_offset_days),
        status=status,
    )


def claim_url(occ):
    return reverse("chores:occurrence_claim", args=[occ.pk])


def complete_url(occ):
    return reverse("chores:occurrence_complete", args=[occ.pk])


# --- credit capture on completion ----------------------------------


@pytest.mark.django_db
def test_non_owner_completion_writes_one_credit_with_expected_value(
    client, signed_in_alice, alice_m, bob_m, nest
):
    chore = make_chore(nest, owner=bob_m, minutes=30, difficulty=5)
    occ = make_occurrence(chore)

    client.post(complete_url(occ))

    credit = ContributionCredit.objects.get()
    assert credit.completion.occurrence == occ
    assert credit.helper == alice_m
    assert credit.owner == bob_m
    assert credit.workload_value == workload_value(30, 5)
    assert credit.workload_value == 45.0


@pytest.mark.django_db
def test_owner_completing_own_occurrence_writes_no_credit(
    client, signed_in_alice, alice_m, nest
):
    occ = make_occurrence(make_chore(nest, owner=alice_m))
    client.post(complete_url(occ))
    assert Completion.objects.count() == 1
    assert ContributionCredit.objects.count() == 0


@pytest.mark.django_db
def test_ownerless_chore_completion_writes_no_credit(
    client, signed_in_alice, alice_m, bob_m, nest
):
    occ = make_occurrence(make_chore(nest, owner=None))
    client.post(complete_url(occ))
    assert Completion.objects.count() == 1
    assert ContributionCredit.objects.count() == 0


@pytest.mark.django_db
def test_credit_uses_chore_estimate_not_completion_actuals(
    client, signed_in_alice, alice_m, bob_m, nest
):
    chore = make_chore(nest, owner=bob_m, minutes=30, difficulty=3)
    occ = make_occurrence(chore)

    client.post(complete_url(occ), {"actual_minutes": 999, "actual_effort": 5})

    credit = ContributionCredit.objects.get()
    assert credit.workload_value == workload_value(30, 3) == 30.0


@pytest.mark.django_db
def test_claim_then_complete_by_claimer_sets_claimed_by_and_credits(
    client, signed_in_alice, alice_m, bob_m, nest
):
    chore = make_chore(nest, owner=bob_m, minutes=20, difficulty=1)
    occ = make_occurrence(chore)

    client.post(claim_url(occ))
    occ.refresh_from_db()
    assert occ.claimed_by == alice_m

    client.post(complete_url(occ))

    credit = ContributionCredit.objects.get()
    assert credit.helper == alice_m
    assert credit.owner == bob_m
    assert credit.workload_value == workload_value(20, 1) == 10.0
    occ.refresh_from_db()
    assert occ.claimed_by == alice_m


@pytest.mark.django_db
def test_reposting_complete_on_completed_occurrence_adds_no_second_credit(
    client, signed_in_alice, alice_m, bob_m, nest, list_url
):
    occ = make_occurrence(make_chore(nest, owner=bob_m))
    client.post(complete_url(occ))
    assert ContributionCredit.objects.count() == 1

    response = client.post(complete_url(occ))
    assert response.status_code == 302
    assert response.url == list_url
    assert ContributionCredit.objects.count() == 1
    assert Completion.objects.count() == 1


# --- ContributionCredit integrity --------------------------------


@pytest.mark.django_db
def test_full_clean_rejects_self_owned_credit(alice_m, bob_m, nest):
    chore = make_chore(nest, owner=bob_m)
    occ = make_occurrence(chore)
    completion = Completion.objects.create(occurrence=occ, completed_by=alice_m)
    credit = ContributionCredit(
        completion=completion, helper=alice_m, owner=alice_m, workload_value=1.0
    )
    with pytest.raises(ValidationError):
        credit.full_clean()


@pytest.mark.django_db
def test_check_constraint_rejects_self_owned_credit(alice_m, bob_m, nest):
    chore = make_chore(nest, owner=bob_m)
    occ = make_occurrence(chore)
    completion = Completion.objects.create(occurrence=occ, completed_by=alice_m)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ContributionCredit.objects.create(
                completion=completion,
                helper=alice_m,
                owner=alice_m,
                workload_value=1.0,
            )


@pytest.mark.django_db
def test_full_clean_rejects_cross_household_helper_owner(alice_m, nest, other_household):
    outsider = Membership.objects.get(household=other_household)
    chore = make_chore(nest, owner=alice_m)
    occ = make_occurrence(chore)
    completion = Completion.objects.create(occurrence=occ, completed_by=alice_m)
    credit = ContributionCredit(
        completion=completion, helper=alice_m, owner=outsider, workload_value=1.0
    )
    with pytest.raises(ValidationError):
        credit.full_clean()


# --- claiming ------------------------------------------------------


@pytest.mark.django_db
def test_non_owner_claim_sets_claimed_by_and_leaves_owner_unchanged(
    client, signed_in_alice, alice_m, bob_m, nest, list_url
):
    chore = make_chore(nest, owner=bob_m)
    occ = make_occurrence(chore)

    response = client.post(claim_url(occ))
    assert response.status_code == 302
    assert response.url == list_url

    occ.refresh_from_db()
    chore.refresh_from_db()
    assert occ.claimed_by == alice_m
    assert chore.primary_owner == bob_m


@pytest.mark.django_db
def test_reassign_claim_to_the_other_member(
    client, signed_in_alice, alice_m, bob_m, nest
):
    chore = make_chore(nest, owner=bob_m)
    occ = make_occurrence(chore)
    occ.claimed_by = bob_m
    occ.save(update_fields=["claimed_by"])

    client.post(claim_url(occ))

    occ.refresh_from_db()
    assert occ.claimed_by == alice_m


@pytest.mark.django_db
def test_reclaiming_own_claim_is_idempotent_noop(
    client, signed_in_alice, alice_m, bob_m, nest
):
    chore = make_chore(nest, owner=bob_m)
    occ = make_occurrence(chore)
    client.post(claim_url(occ))

    response = client.post(claim_url(occ))
    assert response.status_code == 302
    occ.refresh_from_db()
    assert occ.claimed_by == alice_m
    messages = list(client.get(reverse("chores:occurrence_list")).context["messages"])
    assert any("already claimed" in str(m) for m in messages)


@pytest.mark.django_db
def test_claiming_own_chore_is_a_noop(
    client, signed_in_alice, alice_m, nest
):
    occ = make_occurrence(make_chore(nest, owner=alice_m))
    response = client.post(claim_url(occ))
    assert response.status_code == 302
    occ.refresh_from_db()
    assert occ.claimed_by is None


@pytest.mark.django_db
def test_claiming_completed_occurrence_is_a_noop(
    client, signed_in_alice, alice_m, bob_m, nest
):
    occ = make_occurrence(
        make_chore(nest, owner=bob_m), status=OCCURRENCE_STATUS_COMPLETED
    )
    response = client.post(claim_url(occ))
    assert response.status_code == 302
    occ.refresh_from_db()
    assert occ.claimed_by is None


@pytest.mark.django_db
def test_claim_cross_household_occurrence_is_404(
    client, signed_in_alice, other_household
):
    their_occ = make_occurrence(make_chore(other_household, name="Theirs"))
    response = client.post(claim_url(their_occ))
    assert response.status_code == 404
    their_occ.refresh_from_db()
    assert their_occ.claimed_by is None


@pytest.mark.django_db
def test_claim_unknown_pk_is_404(client, signed_in_alice):
    response = client.post(reverse("chores:occurrence_claim", args=[999999]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_get_on_claim_url_is_405_and_writes_nothing(
    client, signed_in_alice, alice_m, bob_m, nest
):
    occ = make_occurrence(make_chore(nest, owner=bob_m))
    response = client.get(claim_url(occ))
    assert response.status_code == 405
    occ.refresh_from_db()
    assert occ.claimed_by is None


@pytest.mark.django_db
def test_anonymous_visitor_is_redirected_to_login(client, nest, bob_m):
    occ = make_occurrence(make_chore(nest, owner=bob_m))
    response = client.post(claim_url(occ))
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_user_with_no_household_is_redirected_on_claim(client, alice, nest):
    occ = make_occurrence(make_chore(nest))
    client.login(username="alice", password=GOOD_PASSWORD)
    response = client.post(claim_url(occ))
    assert response.status_code == 302
    assert response.url == reverse("chores:household_create")


# --- list template: Claim button visibility ----------------------


@pytest.mark.django_db
def test_claim_button_hidden_on_owners_own_row(
    client, signed_in_alice, alice_m, nest, list_url
):
    occ = make_occurrence(make_chore(nest, name="Alice chore", owner=alice_m))
    body = client.get(list_url).content.decode()
    assert "Alice chore" in body
    assert reverse("chores:occurrence_claim", args=[occ.pk]) not in body
    assert "Claim</button>" not in body


@pytest.mark.django_db
def test_claim_button_shown_for_non_owner(
    client, signed_in_alice, alice_m, bob_m, nest, list_url
):
    occ = make_occurrence(make_chore(nest, name="Bob's chore", owner=bob_m))
    body = client.get(list_url).content.decode()
    assert reverse("chores:occurrence_claim", args=[occ.pk]) in body
    assert "Claim</button>" in body


@pytest.mark.django_db
def test_claimed_row_shows_indicator_and_hides_button_for_claimer(
    client, signed_in_alice, alice_m, bob_m, nest, list_url
):
    occ = make_occurrence(make_chore(nest, name="Bob's chore", owner=bob_m))
    occ.claimed_by = alice_m
    occ.save(update_fields=["claimed_by"])

    body = client.get(list_url).content.decode()
    assert "Claimed by alice" in body
    assert reverse("chores:occurrence_claim", args=[occ.pk]) not in body
