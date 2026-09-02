"""Household creation: model rules, the create view, and the nav link."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from chores.models import Household, Membership

User = get_user_model()

GOOD_PASSWORD = "correct-horse-7"


@pytest.fixture
def new_url():
    return reverse("chores:household_create")


@pytest.fixture
def home_url():
    return reverse("chores:home")


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="alice", password=GOOD_PASSWORD)


@pytest.fixture
def signed_in_alice(client, alice):
    client.login(username="alice", password=GOOD_PASSWORD)
    return alice


# --- model rules ---------------------------------------------------------


@pytest.mark.django_db
def test_one_membership_per_user_is_enforced_by_the_database(alice):
    h1 = Household.objects.create(name="First")
    h2 = Household.objects.create(name="Second")
    Membership.objects.create(user=alice, household=h1)
    with pytest.raises(Exception):
        Membership.objects.create(user=alice, household=h2)


@pytest.mark.django_db
def test_third_membership_in_a_household_is_blocked(alice):
    household = Household.objects.create(name="Full house")
    bob = User.objects.create_user(username="bob", password=GOOD_PASSWORD)
    carol = User.objects.create_user(username="carol", password=GOOD_PASSWORD)
    Membership.objects.create(user=alice, household=household)
    Membership.objects.create(user=bob, household=household)

    with pytest.raises(ValidationError):
        Membership.objects.create(user=carol, household=household)

    assert household.memberships.count() == 2


@pytest.mark.django_db
def test_third_membership_is_blocked_in_admin_form(admin_client):
    household = Household.objects.create(name="Full house")
    u1 = User.objects.create_user(username="u1", password=GOOD_PASSWORD)
    u2 = User.objects.create_user(username="u2", password=GOOD_PASSWORD)
    u3 = User.objects.create_user(username="u3", password=GOOD_PASSWORD)
    Membership.objects.create(user=u1, household=household)
    Membership.objects.create(user=u2, household=household)

    response = admin_client.post(
        reverse("admin:chores_membership_add"),
        {"user": u3.pk, "household": household.pk},
    )
    assert response.status_code == 200
    assert "at most 2 members" in response.content.decode()
    assert Membership.objects.filter(household=household).count() == 2


# --- GET /household/new/ ------------------------------------------------


@pytest.mark.django_db
def test_get_renders_the_form_for_a_user_with_no_household(client, signed_in_alice, new_url):
    response = client.get(new_url)
    assert response.status_code == 200
    body = response.content.decode()
    assert 'name="name"' in body
    assert "Create a household" in body


@pytest.mark.django_db
def test_anonymous_visitor_is_redirected_to_login(client, new_url):
    response = client.get(new_url)
    assert response.status_code == 302
    assert reverse("login") in response.url


# --- POST /household/new/ ---------------------------------------------


@pytest.mark.django_db
def test_valid_post_creates_household_and_membership_then_redirects(
    client, signed_in_alice, new_url, home_url
):
    response = client.post(new_url, {"name": "The Nest"})
    assert response.status_code == 302
    assert response.url == home_url

    household = Household.objects.get()
    assert household.name == "The Nest"
    assert list(household.memberships.values_list("user", flat=True)) == [signed_in_alice.pk]


@pytest.mark.django_db
@pytest.mark.parametrize("bad_name", ["", "   ", "\t\n"])
def test_blank_or_whitespace_name_is_rejected_and_creates_nothing(
    client, signed_in_alice, new_url, bad_name
):
    response = client.post(new_url, {"name": bad_name})
    assert response.status_code == 200
    assert Household.objects.count() == 0
    assert Membership.objects.count() == 0


# --- user who already has a household ---------------------------------


@pytest.mark.django_db
def test_user_with_a_household_is_redirected_on_get_with_a_message(
    client, signed_in_alice, new_url, home_url
):
    household = Household.objects.create(name="Existing")
    Membership.objects.create(user=signed_in_alice, household=household)

    response = client.get(new_url, follow=True)
    assert response.redirect_chain[-1][0] == home_url
    assert any("already belong" in str(m) for m in response.context["messages"])


@pytest.mark.django_db
def test_user_with_a_household_is_redirected_on_post_and_nothing_created(
    client, signed_in_alice, new_url, home_url
):
    household = Household.objects.create(name="Existing")
    Membership.objects.create(user=signed_in_alice, household=household)

    response = client.post(new_url, {"name": "Another one"})
    assert response.status_code == 302
    assert response.url == home_url
    assert Household.objects.count() == 1
    assert not Household.objects.filter(name="Another one").exists()
    assert Membership.objects.count() == 1


# --- nav link visibility --------------------------------------------


@pytest.mark.django_db
def test_nav_link_shows_for_signed_in_user_without_a_household(client, signed_in_alice, home_url):
    body = client.get(home_url).content.decode()
    assert reverse("chores:household_create") in body
    assert "Create a household" in body


@pytest.mark.django_db
def test_nav_link_hidden_for_user_with_a_household(client, signed_in_alice, home_url):
    household = Household.objects.create(name="Existing")
    Membership.objects.create(user=signed_in_alice, household=household)

    body = client.get(home_url).content.decode()
    assert reverse("chores:household_create") not in body


@pytest.mark.django_db
def test_nav_link_hidden_for_anonymous_visitor(client, home_url):
    body = client.get(home_url).content.decode()
    assert reverse("chores:household_create") not in body
