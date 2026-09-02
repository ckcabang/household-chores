"""Chore management: the model rules, the household-scoped CBVs, and the nav."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from chores.models import Chore, Household, Membership

User = get_user_model()

GOOD_PASSWORD = "correct-horse-7"


# --- fixtures ----------------------------------------------------------


@pytest.fixture
def list_url():
    return reverse("chores:chore_list")


@pytest.fixture
def create_url():
    return reverse("chores:chore_create")


@pytest.fixture
def household_create_url():
    return reverse("chores:household_create")


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


def valid_payload(**overrides):
    data = {
        "name": "Dishes",
        "description": "",
        "cadence_days": 2,
        "estimated_minutes": 15,
        "difficulty": 3,
        "primary_owner": "",
        "allows_multiple_contributors": "",
    }
    data.update(overrides)
    return data


# --- model rules -----------------------------------------------------


@pytest.mark.django_db
def test_primary_owner_from_another_household_is_rejected(nest, other_household):
    outsider = other_household.memberships.get()
    chore = Chore(
        household=nest,
        name="Vacuum",
        cadence_days=7,
        estimated_minutes=20,
        difficulty=2,
        primary_owner=outsider,
    )
    with pytest.raises(ValidationError):
        chore.full_clean()


@pytest.mark.django_db
def test_primary_owner_in_the_same_household_is_accepted(nest, alice_membership):
    chore = Chore(
        household=nest,
        name="Vacuum",
        cadence_days=7,
        estimated_minutes=20,
        difficulty=2,
        primary_owner=alice_membership,
    )
    chore.full_clean()  # does not raise


# --- list scoping ---------------------------------------------------


@pytest.mark.django_db
def test_list_shows_only_the_current_households_chores(
    client, signed_in_alice, nest, other_household, list_url
):
    Chore.objects.create(
        household=nest, name="Ours", cadence_days=1, estimated_minutes=5, difficulty=1
    )
    Chore.objects.create(
        household=other_household,
        name="Theirs",
        cadence_days=1,
        estimated_minutes=5,
        difficulty=1,
    )

    body = client.get(list_url).content.decode()
    assert "Ours" in body
    assert "Theirs" not in body


# --- create -------------------------------------------------------


@pytest.mark.django_db
def test_create_adds_a_chore_to_the_current_household(
    client, signed_in_alice, nest, list_url, create_url
):
    response = client.post(create_url, valid_payload(name="Trash"))
    assert response.status_code == 302
    assert response.url == list_url

    chore = Chore.objects.get()
    assert chore.name == "Trash"
    assert chore.household == nest


@pytest.mark.django_db
def test_create_accepts_a_primary_owner_in_the_household(
    client, signed_in_alice, alice_membership, create_url
):
    response = client.post(
        create_url, valid_payload(primary_owner=alice_membership.pk)
    )
    assert response.status_code == 302
    assert Chore.objects.get().primary_owner == alice_membership


@pytest.mark.django_db
def test_create_rejects_a_primary_owner_from_another_household(
    client, signed_in_alice, other_household, create_url
):
    outsider = other_household.memberships.get()
    response = client.post(create_url, valid_payload(primary_owner=outsider.pk))
    assert response.status_code == 200
    assert Chore.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"name": "   "},
        {"cadence_days": 0},
        {"cadence_days": -3},
        {"estimated_minutes": 0},
        {"difficulty": 9},
    ],
)
def test_invalid_input_rerenders_and_saves_nothing(
    client, signed_in_alice, create_url, overrides
):
    response = client.post(create_url, valid_payload(**overrides))
    assert response.status_code == 200
    assert Chore.objects.count() == 0


# --- edit --------------------------------------------------------


@pytest.mark.django_db
def test_edit_updates_a_chore(client, signed_in_alice, nest, list_url):
    chore = Chore.objects.create(
        household=nest, name="Old", cadence_days=3, estimated_minutes=10, difficulty=2
    )
    url = reverse("chores:chore_edit", args=[chore.pk])

    response = client.post(url, valid_payload(name="New", cadence_days=5))
    assert response.status_code == 302
    assert response.url == list_url

    chore.refresh_from_db()
    assert chore.name == "New"
    assert chore.cadence_days == 5


@pytest.mark.django_db
def test_edit_of_another_households_chore_is_404(
    client, signed_in_alice, other_household
):
    chore = Chore.objects.create(
        household=other_household,
        name="Theirs",
        cadence_days=1,
        estimated_minutes=5,
        difficulty=1,
    )
    response = client.get(reverse("chores:chore_edit", args=[chore.pk]))
    assert response.status_code == 404


# --- delete -----------------------------------------------------


@pytest.mark.django_db
def test_get_delete_shows_a_confirmation_page(client, signed_in_alice, nest):
    chore = Chore.objects.create(
        household=nest, name="Bins", cadence_days=7, estimated_minutes=5, difficulty=1
    )
    response = client.get(reverse("chores:chore_delete", args=[chore.pk]))
    assert response.status_code == 200
    assert "Bins" in response.content.decode()


@pytest.mark.django_db
def test_post_delete_removes_the_chore(client, signed_in_alice, nest, list_url):
    chore = Chore.objects.create(
        household=nest, name="Bins", cadence_days=7, estimated_minutes=5, difficulty=1
    )
    response = client.post(reverse("chores:chore_delete", args=[chore.pk]))
    assert response.status_code == 302
    assert response.url == list_url
    assert not Chore.objects.filter(pk=chore.pk).exists()


@pytest.mark.django_db
def test_delete_of_another_households_chore_is_404(
    client, signed_in_alice, other_household
):
    chore = Chore.objects.create(
        household=other_household,
        name="Theirs",
        cadence_days=1,
        estimated_minutes=5,
        difficulty=1,
    )
    response = client.post(reverse("chores:chore_delete", args=[chore.pk]))
    assert response.status_code == 404
    assert Chore.objects.filter(pk=chore.pk).exists()


# --- auth / household gating ---------------------------------------


@pytest.mark.django_db
def test_anonymous_visitor_is_redirected_to_login(client, list_url):
    response = client.get(list_url)
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_signed_in_user_with_no_household_is_redirected_to_household_create(
    client, alice, list_url, household_create_url
):
    client.login(username="alice", password=GOOD_PASSWORD)
    response = client.get(list_url)
    assert response.status_code == 302
    assert response.url == household_create_url


@pytest.mark.django_db
def test_no_household_redirect_also_applies_to_post(
    client, alice, create_url, household_create_url
):
    client.login(username="alice", password=GOOD_PASSWORD)
    response = client.post(create_url, valid_payload())
    assert response.status_code == 302
    assert response.url == household_create_url
    assert Chore.objects.count() == 0


# --- nav link visibility -----------------------------------------


def _nav_link_html():
    return f'href="{reverse("chores:chore_list")}">Chores</a>'


@pytest.mark.django_db
def test_nav_shows_chores_link_for_a_user_in_a_household(client, signed_in_alice):
    body = client.get(reverse("chores:home")).content.decode()
    assert _nav_link_html() in body


@pytest.mark.django_db
def test_nav_hides_chores_link_for_a_user_with_no_household(client, alice):
    client.login(username="alice", password=GOOD_PASSWORD)
    body = client.get(reverse("chores:home")).content.decode()
    assert _nav_link_html() not in body


@pytest.mark.django_db
def test_nav_hides_chores_link_for_an_anonymous_visitor(client):
    body = client.get(reverse("chores:home")).content.decode()
    assert _nav_link_html() not in body
