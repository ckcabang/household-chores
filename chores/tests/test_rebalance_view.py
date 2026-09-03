"""The /household/rebalance/ preview view. It must never write anything."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from chores.models import (
    Chore,
    ChoreOccurrence,
    Completion,
    Constraint,
    Household,
    Membership,
    OCCURRENCE_STATUS_ACTIVE,
)

User = get_user_model()
PW = "correct-horse-7"


@pytest.fixture
def url():
    return reverse("chores:rebalance")


@pytest.fixture
def nest(db):
    return Household.objects.create(name="The Nest")


@pytest.fixture
def alice_m(db, nest):
    u = User.objects.create_user(username="alice", password=PW)
    return Membership.objects.create(user=u, household=nest)


@pytest.fixture
def bob_m(db, nest):
    u = User.objects.create_user(username="bob", password=PW)
    return Membership.objects.create(user=u, household=nest)


@pytest.fixture
def signed_in_alice(client, alice_m):
    client.login(username="alice", password=PW)
    return alice_m


def make_chore(nest, name, owner, minutes=30, difficulty=3):
    chore = Chore.objects.create(
        household=nest,
        name=name,
        cadence_days=7,
        estimated_minutes=minutes,
        difficulty=difficulty,
        primary_owner=owner,
    )
    ChoreOccurrence.objects.create(
        chore=chore,
        due_date=timezone.localdate(),
        status=OCCURRENCE_STATUS_ACTIVE,
    )
    return chore


@pytest.mark.django_db
def test_member_sees_current_and_proposed_owners(
    client, signed_in_alice, bob_m, nest, url
):
    # Both chores owned by Alice; Bob is idle, so the preview should move work.
    make_chore(nest, "Dishes", owner=signed_in_alice)
    make_chore(nest, "Laundry", owner=signed_in_alice)

    response = client.get(url)
    assert response.status_code == 200
    body = response.content.decode()
    assert "Dishes" in body and "Laundry" in body
    assert "bob" in body  # proposed to the idle member

    rows = response.context["rows"]
    assert any(r["proposed_owner"] == bob_m for r in rows)


@pytest.mark.django_db
def test_view_writes_nothing(client, signed_in_alice, bob_m, nest, url):
    chore = make_chore(nest, "Dishes", owner=signed_in_alice)
    completion_count = Completion.objects.count()

    client.get(url)

    chore.refresh_from_db()
    assert chore.primary_owner == signed_in_alice
    assert Completion.objects.count() == completion_count


@pytest.mark.django_db
def test_both_excluded_chore_is_shown_unassignable(
    client, signed_in_alice, bob_m, nest, url
):
    chore = make_chore(nest, "Nobody's job", owner=None)
    Constraint.objects.create(chore=chore, membership=signed_in_alice, kind="exclude")
    Constraint.objects.create(chore=chore, membership=bob_m, kind="exclude")

    body = client.get(url).content.decode()
    assert "Unassignable" in body


@pytest.mark.django_db
def test_no_upcoming_chores_renders_empty_state(client, signed_in_alice, nest, url):
    body = client.get(url).content.decode()
    assert "No upcoming chores" in body


@pytest.mark.django_db
def test_anonymous_visitor_redirected_to_login(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_user_with_no_household_redirected_to_onboarding(client, db, url):
    User.objects.create_user(username="loner", password=PW)
    client.login(username="loner", password=PW)
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == reverse("chores:household_create")
