"""Completing an occurrence: the list page, the mark-done POST, and scoping."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from chores.models import (
    Chore,
    ChoreOccurrence,
    Completion,
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
def alice(db):
    return User.objects.create_user(username="alice", password=GOOD_PASSWORD)


@pytest.fixture
def nest(db):
    return Household.objects.create(name="The Nest")


@pytest.fixture
def alice_membership(alice, nest):
    return Membership.objects.create(user=alice, household=nest)


@pytest.fixture
def signed_in_alice(client, alice, alice_membership):
    client.login(username="alice", password=GOOD_PASSWORD)
    return alice


@pytest.fixture
def other_household(db):
    house = Household.objects.create(name="Next door")
    bob = User.objects.create_user(username="bob", password=GOOD_PASSWORD)
    Membership.objects.create(user=bob, household=house)
    return house


def make_chore(household, name="Dishes"):
    return Chore.objects.create(
        household=household,
        name=name,
        cadence_days=2,
        estimated_minutes=15,
        difficulty=3,
    )


def make_occurrence(chore, *, due_offset_days=0, status=OCCURRENCE_STATUS_ACTIVE):
    return ChoreOccurrence.objects.create(
        chore=chore,
        due_date=timezone.localdate() + timedelta(days=due_offset_days),
        status=status,
    )


def complete_url(occurrence):
    return reverse("chores:occurrence_complete", args=[occurrence.pk])


# --- list page ------------------------------------------------------


@pytest.mark.django_db
def test_list_shows_only_this_households_active_occurrences(
    client, signed_in_alice, nest, other_household, list_url
):
    make_occurrence(make_chore(nest, "Ours"))
    make_occurrence(make_chore(other_household, "Theirs"))
    make_occurrence(
        make_chore(nest, "Done already"), status=OCCURRENCE_STATUS_COMPLETED
    )

    body = client.get(list_url).content.decode()
    assert "Ours" in body
    assert "Theirs" not in body
    assert "Done already" not in body


@pytest.mark.django_db
def test_list_flags_overdue_occurrences(client, signed_in_alice, nest, list_url):
    make_occurrence(make_chore(nest, "Late one"), due_offset_days=-3)
    body = client.get(list_url).content.decode()
    assert "Overdue" in body


@pytest.mark.django_db
def test_empty_list_renders_a_clean_state(client, signed_in_alice, list_url):
    response = client.get(list_url)
    assert response.status_code == 200
    assert "Nothing due" in response.content.decode()


# --- mark done -----------------------------------------------------


@pytest.mark.django_db
def test_complete_without_feedback(
    client, signed_in_alice, alice_membership, nest, list_url
):
    occ = make_occurrence(make_chore(nest))
    response = client.post(complete_url(occ))
    assert response.status_code == 302
    assert response.url == list_url

    occ.refresh_from_db()
    assert occ.status == OCCURRENCE_STATUS_COMPLETED
    assert occ.completed_at is not None

    completion = Completion.objects.get()
    assert completion.occurrence == occ
    assert completion.completed_by == alice_membership
    assert completion.actual_minutes is None
    assert completion.actual_effort is None


@pytest.mark.django_db
def test_complete_with_feedback_stores_actual_values(
    client, signed_in_alice, alice_membership, nest
):
    occ = make_occurrence(make_chore(nest))
    response = client.post(
        complete_url(occ), {"actual_minutes": 25, "actual_effort": 4}
    )
    assert response.status_code == 302

    completion = Completion.objects.get()
    assert completion.actual_minutes == 25
    assert completion.actual_effort == 4
    assert completion.completed_by == alice_membership


@pytest.mark.django_db
def test_double_complete_is_a_guarded_no_op(
    client, signed_in_alice, nest, list_url
):
    occ = make_occurrence(make_chore(nest))
    client.post(complete_url(occ), {"actual_minutes": 10})
    first = Completion.objects.get()
    first_completed_at = ChoreOccurrence.objects.get(pk=occ.pk).completed_at

    response = client.post(complete_url(occ), {"actual_minutes": 99})
    assert response.status_code == 302
    assert response.url == list_url

    assert Completion.objects.count() == 1
    assert Completion.objects.get().pk == first.pk
    assert Completion.objects.get().actual_minutes == 10
    assert ChoreOccurrence.objects.get(pk=occ.pk).completed_at == first_completed_at


@pytest.mark.django_db
def test_cross_household_occurrence_is_404(
    client, signed_in_alice, other_household
):
    their_occ = make_occurrence(make_chore(other_household, "Theirs"))
    response = client.post(complete_url(their_occ))
    assert response.status_code == 404
    assert Completion.objects.count() == 0
    their_occ.refresh_from_db()
    assert their_occ.status == OCCURRENCE_STATUS_ACTIVE


@pytest.mark.django_db
def test_unknown_pk_is_404(client, signed_in_alice):
    response = client.post(reverse("chores:occurrence_complete", args=[999999]))
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {"actual_minutes": 0},
        {"actual_minutes": -5},
        {"actual_effort": 9},
        {"actual_effort": 0},
    ],
)
def test_invalid_actual_values_rerender_and_write_nothing(
    client, signed_in_alice, nest, payload
):
    occ = make_occurrence(make_chore(nest))
    response = client.post(complete_url(occ), payload)
    assert response.status_code == 200

    occ.refresh_from_db()
    assert occ.status == OCCURRENCE_STATUS_ACTIVE
    assert occ.completed_at is None
    assert Completion.objects.count() == 0


@pytest.mark.django_db
def test_get_on_complete_url_is_405_and_mutates_nothing(
    client, signed_in_alice, nest
):
    occ = make_occurrence(make_chore(nest))
    response = client.get(complete_url(occ))
    assert response.status_code == 405
    occ.refresh_from_db()
    assert occ.status == OCCURRENCE_STATUS_ACTIVE
    assert Completion.objects.count() == 0


# --- auth / household gating -------------------------------------


@pytest.mark.django_db
def test_anonymous_visitor_is_redirected_to_login(client, list_url):
    response = client.get(list_url)
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_user_with_no_household_is_redirected_on_list(client, alice, list_url):
    client.login(username="alice", password=GOOD_PASSWORD)
    response = client.get(list_url)
    assert response.status_code == 302
    assert response.url == reverse("chores:household_create")


@pytest.mark.django_db
def test_user_with_no_household_is_redirected_on_complete(client, alice, nest):
    occ = make_occurrence(make_chore(nest))
    client.login(username="alice", password=GOOD_PASSWORD)
    response = client.post(complete_url(occ))
    assert response.status_code == 302
    assert response.url == reverse("chores:household_create")
    assert Completion.objects.count() == 0


# --- nav link visibility --------------------------------------


def _nav_link_html():
    return f'href="{reverse("chores:occurrence_list")}">Occurrences</a>'


@pytest.mark.django_db
def test_nav_shows_occurrences_link_for_a_user_in_a_household(
    client, signed_in_alice
):
    body = client.get(reverse("chores:home")).content.decode()
    assert _nav_link_html() in body


@pytest.mark.django_db
def test_nav_hides_occurrences_link_for_a_user_with_no_household(client, alice):
    client.login(username="alice", password=GOOD_PASSWORD)
    body = client.get(reverse("chores:home")).content.decode()
    assert _nav_link_html() not in body


@pytest.mark.django_db
def test_nav_hides_occurrences_link_for_an_anonymous_visitor(client):
    body = client.get(reverse("chores:home")).content.decode()
    assert _nav_link_html() not in body
