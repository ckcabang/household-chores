"""People-to-chore constraints: the model rule, the POST-only views, the UI."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from chores.models import Chore, Constraint, Household, Membership

User = get_user_model()

GOOD_PASSWORD = "correct-horse-7"


# --- fixtures --------------------------------------------------------


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
def chore(nest):
    return Chore.objects.create(
        household=nest,
        name="Dishes",
        cadence_days=2,
        estimated_minutes=15,
        difficulty=3,
    )


@pytest.fixture
def other_household(db):
    house = Household.objects.create(name="Next door")
    bob = User.objects.create_user(username="bob", password=GOOD_PASSWORD)
    Membership.objects.create(user=bob, household=house)
    return house


def add_url(chore):
    return reverse("chores:constraint_add", args=[chore.pk])


def delete_url(chore, constraint):
    return reverse("chores:constraint_delete", args=[chore.pk, constraint.pk])


def edit_url(chore):
    return reverse("chores:chore_edit", args=[chore.pk])


# --- model rule -----------------------------------------------------


@pytest.mark.django_db
def test_constraint_across_households_is_rejected(chore, other_household):
    outsider = other_household.memberships.get()
    constraint = Constraint(chore=chore, membership=outsider, kind="prefer")
    with pytest.raises(ValidationError):
        constraint.full_clean()


@pytest.mark.django_db
def test_constraint_in_the_same_household_is_accepted(chore, alice_membership):
    constraint = Constraint(
        chore=chore, membership=alice_membership, kind="prefer"
    )
    constraint.full_clean()  # does not raise


# --- add ----------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["prefer", "exclude"])
def test_add_creates_a_constraint(
    client, signed_in_alice, alice_membership, chore, kind
):
    response = client.post(
        add_url(chore), {"membership": alice_membership.pk, "kind": kind}
    )
    assert response.status_code == 302
    assert response.url == edit_url(chore)

    constraint = Constraint.objects.get()
    assert constraint.chore == chore
    assert constraint.membership == alice_membership
    assert constraint.kind == kind


@pytest.mark.django_db
def test_second_constraint_for_same_person_and_chore_is_rejected(
    client, signed_in_alice, alice_membership, chore
):
    Constraint.objects.create(
        chore=chore, membership=alice_membership, kind="prefer"
    )
    response = client.post(
        add_url(chore),
        {"membership": alice_membership.pk, "kind": "exclude"},
        follow=True,
    )
    assert response.status_code == 200
    assert "already has a constraint" in response.content.decode()

    constraint = Constraint.objects.get()
    assert constraint.kind == "prefer"  # unchanged, not replaced


@pytest.mark.django_db
def test_add_for_another_households_chore_is_404(
    client, signed_in_alice, alice_membership, other_household
):
    their_chore = Chore.objects.create(
        household=other_household,
        name="Theirs",
        cadence_days=1,
        estimated_minutes=5,
        difficulty=1,
    )
    response = client.post(
        add_url(their_chore),
        {"membership": alice_membership.pk, "kind": "prefer"},
    )
    assert response.status_code == 404
    assert Constraint.objects.count() == 0


@pytest.mark.django_db
def test_add_with_a_membership_from_another_household_is_404(
    client, signed_in_alice, chore, other_household
):
    outsider = other_household.memberships.get()
    response = client.post(
        add_url(chore), {"membership": outsider.pk, "kind": "prefer"}
    )
    assert response.status_code == 404
    assert Constraint.objects.count() == 0


@pytest.mark.django_db
def test_add_rejects_get_and_mutates_nothing(
    client, signed_in_alice, alice_membership, chore
):
    response = client.get(add_url(chore))
    assert response.status_code == 405
    assert Constraint.objects.count() == 0


# --- delete ------------------------------------------------------


@pytest.mark.django_db
def test_delete_removes_the_constraint(
    client, signed_in_alice, alice_membership, chore
):
    constraint = Constraint.objects.create(
        chore=chore, membership=alice_membership, kind="prefer"
    )
    response = client.post(delete_url(chore, constraint))
    assert response.status_code == 302
    assert response.url == edit_url(chore)
    assert not Constraint.objects.filter(pk=constraint.pk).exists()


@pytest.mark.django_db
def test_delete_of_another_households_constraint_is_404(
    client, signed_in_alice, other_household
):
    their_chore = Chore.objects.create(
        household=other_household,
        name="Theirs",
        cadence_days=1,
        estimated_minutes=5,
        difficulty=1,
    )
    their_constraint = Constraint.objects.create(
        chore=their_chore,
        membership=other_household.memberships.get(),
        kind="prefer",
    )
    response = client.post(
        reverse(
            "chores:constraint_delete",
            args=[their_chore.pk, their_constraint.pk],
        )
    )
    assert response.status_code == 404
    assert Constraint.objects.filter(pk=their_constraint.pk).exists()


@pytest.mark.django_db
def test_delete_rejects_get_and_mutates_nothing(
    client, signed_in_alice, alice_membership, chore
):
    constraint = Constraint.objects.create(
        chore=chore, membership=alice_membership, kind="prefer"
    )
    response = client.get(delete_url(chore, constraint))
    assert response.status_code == 405
    assert Constraint.objects.filter(pk=constraint.pk).exists()


# --- household gating --------------------------------------------


@pytest.mark.django_db
def test_anonymous_visitor_is_redirected_to_login(client, chore):
    response = client.post(add_url(chore))
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_user_with_no_household_is_redirected_to_household_create(
    client, alice, chore
):
    client.login(username="alice", password=GOOD_PASSWORD)
    response = client.post(add_url(chore))
    assert response.status_code == 302
    assert response.url == reverse("chores:household_create")
    assert Constraint.objects.count() == 0


# --- UI --------------------------------------------------------


@pytest.mark.django_db
def test_edit_page_lists_constraints_and_the_add_form(
    client, signed_in_alice, alice_membership, chore
):
    Constraint.objects.create(
        chore=chore, membership=alice_membership, kind="exclude"
    )
    body = client.get(edit_url(chore)).content.decode()
    assert "Constraints" in body
    assert "alice" in body
    assert "Excluded" in body
    assert add_url(chore) in body
    # person dropdown is scoped to this household's memberships
    assert f'value="{alice_membership.pk}"' in body


@pytest.mark.django_db
def test_edit_page_dropdown_excludes_other_households(
    client, signed_in_alice, chore, other_household
):
    other_household.memberships.get()  # user "bob", another household
    body = client.get(edit_url(chore)).content.decode()
    assert "bob" not in body


@pytest.mark.django_db
def test_chore_list_shows_a_constraint_summary(
    client, signed_in_alice, alice_membership, chore
):
    Constraint.objects.create(
        chore=chore, membership=alice_membership, kind="prefer"
    )
    body = client.get(reverse("chores:chore_list")).content.decode()
    assert "alice: preferred" in body


@pytest.mark.django_db
def test_chore_list_shows_none_when_a_chore_has_no_constraints(
    client, signed_in_alice, chore
):
    body = client.get(reverse("chores:chore_list")).content.decode()
    assert "None" in body
