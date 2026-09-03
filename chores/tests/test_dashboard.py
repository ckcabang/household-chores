"""The /dashboard/ screen: occurrences window, balance, history, mark-done."""

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
PW = "correct-horse-7"


@pytest.fixture
def url():
    return reverse("chores:dashboard")


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


def make_chore(nest, name="Dishes", owner=None, minutes=30, difficulty=3):
    return Chore.objects.create(
        household=nest,
        name=name,
        cadence_days=7,
        estimated_minutes=minutes,
        difficulty=difficulty,
        primary_owner=owner,
    )


def make_occ(chore, due_offset, status=OCCURRENCE_STATUS_ACTIVE):
    return ChoreOccurrence.objects.create(
        chore=chore,
        due_date=timezone.localdate() + timedelta(days=due_offset),
        status=status,
    )


# --- access ---------------------------------------------------


@pytest.mark.django_db
def test_anonymous_redirected_to_login(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_user_without_household_redirected_to_onboarding(client, db, url):
    User.objects.create_user(username="loner", password=PW)
    client.login(username="loner", password=PW)
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == reverse("chores:household_create")


@pytest.mark.django_db
def test_nav_has_a_dashboard_link(client, as_alice, url):
    body = client.get(reverse("chores:home")).content.decode()
    assert url in body


# --- occurrence window --------------------------------------


@pytest.mark.django_db
def test_lists_overdue_and_soon_but_not_far_or_done(client, as_alice, nest, url):
    chore = make_chore(nest, "Dishes", owner=as_alice)
    overdue = make_occ(chore, -3)
    soon = make_occ(chore, 5)
    make_occ(chore, 40)  # beyond the 14-day window
    make_occ(chore, 1, status=OCCURRENCE_STATUS_COMPLETED)

    response = client.get(url)
    listed = {o.pk for o in response.context["occurrences"]}
    assert overdue.pk in listed
    assert soon.pk in listed
    assert len(listed) == 2

    body = response.content.decode()
    assert "Overdue" in body


@pytest.mark.django_db
def test_empty_states_render(client, as_alice, nest, url):
    body = client.get(url).content.decode()
    assert "Nothing due" in body
    assert "Nothing completed in the last 30 days" in body


# --- balance + history --------------------------------------


@pytest.mark.django_db
def test_balance_reflects_completions(client, as_alice, bob_m, nest, url):
    chore = make_chore(nest, "Vacuum", owner=as_alice, minutes=60)
    for offset in (-1, -2, -3):
        occ = make_occ(chore, offset, status=OCCURRENCE_STATUS_COMPLETED)
        occ.completed_at = timezone.now() - timedelta(days=abs(offset))
        occ.save(update_fields=["completed_at"])
        Completion.objects.create(occurrence=occ, completed_by=as_alice)

    response = client.get(url)
    balance = {row["member"].pk: row for row in response.context["balance"]}
    assert balance[as_alice.pk]["workload"] > balance[bob_m.pk]["workload"]
    assert balance[as_alice.pk]["is_ahead"] is True

    contribution = {row["member"].pk: row for row in response.context["contribution"]}
    assert contribution[as_alice.pk]["completions"] == 3


@pytest.mark.django_db
def test_credit_shows_in_the_contribution_summary(client, as_alice, bob_m, nest, url):
    chore = make_chore(nest, "Bob's chore", owner=bob_m)
    occ = make_occ(chore, 0)
    client.post(reverse("chores:occurrence_complete", args=[occ.pk]))

    contribution = {
        row["member"].pk: row
        for row in client.get(url).context["contribution"]
    }
    assert contribution[as_alice.pk]["credits"] == 1


# --- mark done from the dashboard -------------------------


@pytest.mark.django_db
def test_mark_done_from_dashboard_returns_to_dashboard(client, as_alice, nest, url):
    chore = make_chore(nest, "Dishes", owner=as_alice)
    occ = make_occ(chore, 0)

    response = client.post(
        reverse("chores:occurrence_complete", args=[occ.pk]),
        {"next": url},
    )
    assert response.status_code == 302
    assert response.url == url

    occ.refresh_from_db()
    assert occ.status == OCCURRENCE_STATUS_COMPLETED


@pytest.mark.django_db
def test_seeded_numbers_match_the_page(client, as_alice, bob_m, nest, url):
    a_chore = make_chore(nest, "A", owner=as_alice, minutes=30)
    for offset in (-1, -2):
        occ = make_occ(a_chore, offset, status=OCCURRENCE_STATUS_COMPLETED)
        occ.completed_at = timezone.now() - timedelta(days=abs(offset))
        occ.save(update_fields=["completed_at"])
        Completion.objects.create(occurrence=occ, completed_by=as_alice)

    body = client.get(url).content.decode()
    # Two completions by alice, zero by bob.
    assert ">2<" in body
