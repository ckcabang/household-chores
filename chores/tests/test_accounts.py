"""Signup, login, and logout using django.contrib.auth."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

# A password that clears every AUTH_PASSWORD_VALIDATORS check.
GOOD_PASSWORD = "correct-horse-7"


@pytest.fixture
def home_url():
    return reverse("chores:home")


@pytest.mark.django_db
def test_signup_get_renders_form(client):
    response = client.get(reverse("signup"))
    assert response.status_code == 200
    body = response.content.decode()
    assert "Sign up" in body
    assert 'name="username"' in body
    assert 'name="password1"' in body
    assert 'name="password2"' in body


@pytest.mark.django_db
def test_signup_success_creates_user_logs_in_and_redirects(client, home_url):
    response = client.post(
        reverse("signup"),
        {"username": "alice", "password1": GOOD_PASSWORD, "password2": GOOD_PASSWORD},
    )
    assert response.status_code == 302
    assert response.url == home_url
    assert User.objects.filter(username="alice").exists()
    assert client.session.get("_auth_user_id")


@pytest.mark.django_db
def test_signup_duplicate_username_is_rejected(client):
    User.objects.create_user(username="bob", password=GOOD_PASSWORD)
    response = client.post(
        reverse("signup"),
        {"username": "bob", "password1": GOOD_PASSWORD, "password2": GOOD_PASSWORD},
    )
    assert response.status_code == 200
    assert "already exists" in response.content.decode()
    assert User.objects.filter(username="bob").count() == 1
    assert not client.session.get("_auth_user_id")


@pytest.mark.django_db
def test_signup_password_mismatch_is_rejected(client):
    response = client.post(
        reverse("signup"),
        {"username": "carol", "password1": GOOD_PASSWORD, "password2": "something-else-9"},
    )
    assert response.status_code == 200
    assert "didn" in response.content.decode().lower() or "match" in response.content.decode().lower()
    assert not User.objects.filter(username="carol").exists()


@pytest.mark.django_db
def test_signup_weak_password_is_rejected(client):
    response = client.post(
        reverse("signup"),
        {"username": "dave", "password1": "12345678", "password2": "12345678"},
    )
    assert response.status_code == 200
    assert not User.objects.filter(username="dave").exists()


@pytest.mark.django_db
def test_login_success_redirects_to_home(client, home_url):
    User.objects.create_user(username="erin", password=GOOD_PASSWORD)
    response = client.post(
        reverse("login"), {"username": "erin", "password": GOOD_PASSWORD}
    )
    assert response.status_code == 302
    assert response.url == home_url
    assert client.session.get("_auth_user_id")


@pytest.mark.django_db
def test_login_failure_re_renders_with_error_and_no_session(client):
    User.objects.create_user(username="frank", password=GOOD_PASSWORD)
    response = client.post(
        reverse("login"), {"username": "frank", "password": "wrong-password"}
    )
    assert response.status_code == 200
    assert "Please enter a correct username and password" in response.content.decode()
    assert not client.session.get("_auth_user_id")


@pytest.mark.django_db
def test_logout_ends_session_and_redirects_to_home(client, home_url):
    User.objects.create_user(username="grace", password=GOOD_PASSWORD)
    client.login(username="grace", password=GOOD_PASSWORD)
    assert client.session.get("_auth_user_id")

    response = client.post(reverse("logout"))
    assert response.status_code == 302
    assert response.url == home_url
    assert not client.session.get("_auth_user_id")


@pytest.mark.django_db
def test_authenticated_user_is_redirected_away_from_signup(client, home_url):
    User.objects.create_user(username="heidi", password=GOOD_PASSWORD)
    client.login(username="heidi", password=GOOD_PASSWORD)

    response = client.get(reverse("signup"))
    assert response.status_code == 302
    assert response.url == home_url


@pytest.mark.django_db
def test_authenticated_user_is_redirected_away_from_login(client, home_url):
    User.objects.create_user(username="ivan", password=GOOD_PASSWORD)
    client.login(username="ivan", password=GOOD_PASSWORD)

    response = client.get(reverse("login"))
    assert response.status_code == 302
    assert response.url == home_url


@pytest.mark.django_db
def test_header_nav_reflects_auth_state(client, home_url):
    logged_out = client.get(home_url).content.decode()
    assert "Log in" in logged_out
    assert "Sign up" in logged_out
    assert "Log out" not in logged_out

    User.objects.create_user(username="judy", password=GOOD_PASSWORD)
    client.login(username="judy", password=GOOD_PASSWORD)
    logged_in = client.get(home_url).content.decode()
    assert "Log out" in logged_in
    assert "judy" in logged_in
