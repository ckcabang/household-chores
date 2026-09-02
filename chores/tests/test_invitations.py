"""The signed invite-link flow: model, invite page, accept view, nav, signup."""

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core import signing
from django.urls import reverse

from chores.models import (
    INVITATION_TOKEN_SALT,
    Household,
    Invitation,
    Membership,
)

User = get_user_model()

GOOD_PASSWORD = "correct-horse-7"


@pytest.fixture
def home_url():
    return reverse("chores:home")


@pytest.fixture
def invite_url():
    return reverse("chores:invite")


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="alice", password=GOOD_PASSWORD)


@pytest.fixture
def bob(db):
    return User.objects.create_user(username="bob", password=GOOD_PASSWORD)


@pytest.fixture
def alice_household(alice):
    household = Household.objects.create(name="The Nest")
    Membership.objects.create(user=alice, household=household)
    return household


@pytest.fixture
def signed_in_alice(client, alice):
    client.login(username="alice", password=GOOD_PASSWORD)
    return alice


def accept_url_for(invitation):
    return reverse("chores:invite_accept", args=[invitation.token])


# --- model -------------------------------------------------------------


@pytest.mark.django_db
def test_token_round_trips_to_the_invitation(alice, alice_household):
    invitation = Invitation.objects.create(
        household=alice_household, created_by=alice
    )
    from datetime import timedelta

    assert Invitation.from_token(invitation.token, timedelta(days=7)) == invitation


@pytest.mark.django_db
def test_no_raw_token_is_stored_on_the_row(alice, alice_household):
    invitation = Invitation.objects.create(
        household=alice_household, created_by=alice
    )
    field_names = {f.name for f in Invitation._meta.get_fields()}
    assert "token" not in field_names
    # The token is derived, not persisted.
    assert invitation.token not in str(vars(invitation))


@pytest.mark.django_db
def test_one_invitation_per_household(alice, alice_household):
    Invitation.objects.create(household=alice_household, created_by=alice)
    with pytest.raises(Exception):
        Invitation.objects.create(household=alice_household, created_by=alice)


# --- GET /household/invite/ ------------------------------------------


@pytest.mark.django_db
def test_invite_page_shows_a_shareable_absolute_link(
    client, signed_in_alice, alice_household, invite_url
):
    response = client.get(invite_url)
    assert response.status_code == 200
    invitation = Invitation.objects.get(household=alice_household)
    assert invitation.created_by == signed_in_alice
    body = response.content.decode()
    expected = "http://testserver" + reverse(
        "chores:invite_accept", args=[invitation.token]
    )
    assert expected in body


@pytest.mark.django_db
def test_reloading_the_invite_page_keeps_the_same_invitation(
    client, signed_in_alice, alice_household, invite_url
):
    client.get(invite_url)
    client.get(invite_url)
    assert Invitation.objects.filter(household=alice_household).count() == 1


@pytest.mark.django_db
def test_invite_page_for_a_full_household_offers_no_link(
    client, signed_in_alice, alice_household, bob, invite_url
):
    Membership.objects.create(user=bob, household=alice_household)
    response = client.get(invite_url)
    assert response.status_code == 200
    body = response.content.decode()
    assert "This household is already full." in body
    assert "household/join/" not in body
    assert not Invitation.objects.exists()


@pytest.mark.django_db
def test_invite_page_redirects_anonymous_to_login(client, invite_url):
    response = client.get(invite_url)
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_invite_page_redirects_user_with_no_household_home(
    client, signed_in_alice, invite_url, home_url
):
    response = client.get(invite_url, follow=True)
    assert response.redirect_chain[-1][0] == home_url
    assert any("household" in str(m).lower() for m in response.context["messages"])
    assert not Invitation.objects.exists()


# --- nav link -------------------------------------------------------


@pytest.mark.django_db
def test_nav_shows_invite_link_for_member_of_not_full_household(
    client, signed_in_alice, alice_household, home_url
):
    body = client.get(home_url).content.decode()
    assert reverse("chores:invite") in body
    assert "Invite your partner" in body


@pytest.mark.django_db
def test_nav_hides_invite_link_for_full_household(
    client, signed_in_alice, alice_household, bob, home_url
):
    Membership.objects.create(user=bob, household=alice_household)
    body = client.get(home_url).content.decode()
    assert reverse("chores:invite") not in body


@pytest.mark.django_db
def test_nav_hides_invite_link_for_user_with_no_household(
    client, signed_in_alice, home_url
):
    body = client.get(home_url).content.decode()
    assert reverse("chores:invite") not in body


@pytest.mark.django_db
def test_nav_hides_invite_link_for_anonymous_visitor(client, home_url):
    body = client.get(home_url).content.decode()
    assert reverse("chores:invite") not in body


# --- accept: token validation --------------------------------------


@pytest.mark.django_db
def test_expired_token_is_rejected_and_creates_nothing(
    client, bob, alice, alice_household, settings
):
    invitation = Invitation.objects.create(
        household=alice_household, created_by=alice
    )
    url = accept_url_for(invitation)
    settings.INVITATION_MAX_AGE_DAYS = -1
    client.login(username="bob", password=GOOD_PASSWORD)
    response = client.get(url)
    assert response.status_code == 200
    assert "This invite has expired." in response.content.decode()
    assert Membership.objects.filter(user=bob).count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("bad_token", ["not-a-token", "a.b.c", ""])
def test_malformed_token_yields_404(client, bob, bad_token):
    client.login(username="bob", password=GOOD_PASSWORD)
    response = client.get(f"/household/join/{bad_token or 'x'}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_tampered_token_yields_404(client, bob, alice, alice_household):
    invitation = Invitation.objects.create(
        household=alice_household, created_by=alice
    )
    tampered = invitation.token[:-2] + ("aa" if invitation.token[-1] != "a" else "bb")
    client.login(username="bob", password=GOOD_PASSWORD)
    response = client.get(reverse("chores:invite_accept", args=[tampered]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_unknown_pk_token_yields_404(client, bob):
    token = signing.dumps(999999, salt=INVITATION_TOKEN_SALT)
    client.login(username="bob", password=GOOD_PASSWORD)
    response = client.get(reverse("chores:invite_accept", args=[token]))
    assert response.status_code == 404


# --- accept: logged-out routing ----------------------------------


@pytest.mark.django_db
def test_logged_out_open_redirects_to_login_with_next(client, alice, alice_household):
    invitation = Invitation.objects.create(
        household=alice_household, created_by=alice
    )
    url = accept_url_for(invitation)
    response = client.get(url)
    assert response.status_code == 302
    assert reverse("login") in response.url
    from urllib.parse import quote

    assert quote(url) in response.url


@pytest.mark.django_db
def test_join_completes_after_logging_in(client, bob, alice, alice_household):
    invitation = Invitation.objects.create(
        household=alice_household, created_by=alice
    )
    url = accept_url_for(invitation)
    client.login(username="bob", password=GOOD_PASSWORD)
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == reverse("chores:home")
    assert Membership.objects.filter(user=bob, household=alice_household).exists()


# --- accept: signup routing -------------------------------------


@pytest.mark.django_db
def test_login_page_sign_up_link_carries_next(client, alice, alice_household):
    invitation = Invitation.objects.create(
        household=alice_household, created_by=alice
    )
    url = accept_url_for(invitation)
    response = client.get(reverse("login"), {"next": url})
    body = response.content.decode()
    assert "next=" in body
    assert reverse("signup") in body


@pytest.mark.django_db
def test_signup_redirects_to_safe_next(client, alice, alice_household):
    invitation = Invitation.objects.create(
        household=alice_household, created_by=alice
    )
    url = accept_url_for(invitation)
    response = client.post(
        reverse("signup"),
        {
            "username": "carol",
            "password1": GOOD_PASSWORD,
            "password2": GOOD_PASSWORD,
            "next": url,
        },
    )
    assert response.status_code == 302
    assert response.url == url


@pytest.mark.django_db
def test_signup_ignores_unsafe_next(client, home_url):
    response = client.post(
        reverse("signup"),
        {
            "username": "dave",
            "password1": GOOD_PASSWORD,
            "password2": GOOD_PASSWORD,
            "next": "http://evil.example.com/steal",
        },
    )
    assert response.status_code == 302
    assert response.url == home_url


@pytest.mark.django_db
def test_signup_then_join_completes(client, alice, alice_household):
    invitation = Invitation.objects.create(
        household=alice_household, created_by=alice
    )
    url = accept_url_for(invitation)
    client.post(
        reverse("signup"),
        {
            "username": "carol",
            "password1": GOOD_PASSWORD,
            "password2": GOOD_PASSWORD,
            "next": url,
        },
    )
    response = client.get(url)
    assert response.status_code == 302
    carol = User.objects.get(username="carol")
    assert Membership.objects.filter(user=carol, household=alice_household).exists()


# --- accept: join outcomes -------------------------------------


@pytest.mark.django_db
def test_valid_link_adds_second_membership_and_stamps_invitation(
    client, bob, alice, alice_household, home_url
):
    invitation = Invitation.objects.create(
        household=alice_household, created_by=alice
    )
    url = accept_url_for(invitation)
    client.login(username="bob", password=GOOD_PASSWORD)
    response = client.get(url, follow=True)

    assert response.redirect_chain[-1][0] == home_url
    assert any("welcome" in str(m).lower() for m in response.context["messages"])

    invitation.refresh_from_db()
    assert invitation.accepted_by == bob
    assert invitation.accepted_at is not None
    assert alice_household.memberships.count() == 2


@pytest.mark.django_db
def test_link_for_a_full_household_creates_nothing(
    client, alice, alice_household, bob
):
    invitation = Invitation.objects.create(
        household=alice_household, created_by=alice
    )
    Membership.objects.create(user=bob, household=alice_household)
    carol = User.objects.create_user(username="carol", password=GOOD_PASSWORD)
    client.login(username="carol", password=GOOD_PASSWORD)

    response = client.get(accept_url_for(invitation))
    assert response.status_code == 200
    assert "This household is already full." in response.content.decode()
    assert not Membership.objects.filter(user=carol).exists()


@pytest.mark.django_db
def test_user_who_already_has_a_household_gets_a_clean_message(
    client, alice, alice_household, bob
):
    invitation = Invitation.objects.create(
        household=alice_household, created_by=alice
    )
    other = Household.objects.create(name="Bob's place")
    Membership.objects.create(user=bob, household=other)
    client.login(username="bob", password=GOOD_PASSWORD)

    response = client.get(accept_url_for(invitation))
    assert response.status_code == 200
    assert "already belong" in response.content.decode().lower()
    assert Membership.objects.filter(user=bob).count() == 1


@pytest.mark.django_db
def test_inviter_opening_their_own_link_is_rejected_cleanly(
    client, signed_in_alice, alice_household
):
    invitation = Invitation.objects.create(
        household=alice_household, created_by=signed_in_alice
    )
    response = client.get(accept_url_for(invitation))
    assert response.status_code == 200
    assert "already belong" in response.content.decode().lower()
    assert alice_household.memberships.count() == 1
    invitation.refresh_from_db()
    assert invitation.accepted_by is None


# --- admin ------------------------------------------------------


@pytest.mark.django_db
def test_invitation_is_registered_in_admin():
    assert admin.site.is_registered(Invitation)
    model_admin = admin.site._registry[Invitation]
    assert set(model_admin.list_display) == {
        "household",
        "created_by",
        "created_at",
        "accepted_by",
        "accepted_at",
    }
