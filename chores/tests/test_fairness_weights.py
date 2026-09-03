"""FairnessWeights: the auto-created row, backfill, the edit view, validation."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.urls import reverse

from chores.fairness import (
    DEFAULT_DECAY_HALF_LIFE_DAYS,
    DEFAULT_DIFFICULTY_WEIGHT,
    DEFAULT_TIME_WEIGHT,
)
from chores.models import FairnessWeights, Household, Membership
from chores.signals import create_fairness_weights

User = get_user_model()

GOOD_PASSWORD = "correct-horse-7"


@pytest.fixture
def edit_url():
    return reverse("chores:fairness_edit")


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="alice", password=GOOD_PASSWORD)


@pytest.fixture
def nest(db):
    return Household.objects.create(name="The Nest")


@pytest.fixture
def alice_in_nest(alice, nest):
    Membership.objects.create(user=alice, household=nest)
    return alice


@pytest.fixture
def signed_in_alice(client, alice_in_nest):
    client.login(username="alice", password=GOOD_PASSWORD)
    return alice_in_nest


@pytest.fixture
def legacy_household(db):
    """A household created as if before FairnessWeights existed."""
    post_save.disconnect(create_fairness_weights, sender=Household)
    try:
        household = Household.objects.create(name="Legacy")
    finally:
        post_save.connect(create_fairness_weights, sender=Household)
    return household


# --- creation and backfill -----------------------------------------


@pytest.mark.django_db
def test_creating_a_household_creates_its_weights_with_defaults(nest):
    weights = nest.fairness_weights
    assert weights.time_weight == DEFAULT_TIME_WEIGHT
    assert weights.difficulty_weight == DEFAULT_DIFFICULTY_WEIGHT
    assert weights.decay_half_life_days == DEFAULT_DECAY_HALF_LIFE_DAYS


@pytest.mark.django_db
def test_create_view_gets_a_weights_row(client, alice):
    client.login(username="alice", password=GOOD_PASSWORD)
    client.post(reverse("chores:household_create"), {"name": "Casa"})
    household = Household.objects.get(name="Casa")
    assert FairnessWeights.objects.filter(household=household).exists()


@pytest.mark.django_db
def test_admin_created_household_gets_a_weights_row(admin_client):
    admin_client.post(reverse("admin:chores_household_add"), {"name": "Admin house"})
    household = Household.objects.get(name="Admin house")
    assert FairnessWeights.objects.filter(household=household).count() == 1


@pytest.mark.django_db
def test_legacy_household_has_no_row_until_backfilled(legacy_household):
    assert not FairnessWeights.objects.filter(household=legacy_household).exists()


@pytest.mark.django_db
def test_backfill_query_covers_a_household_missing_its_row(legacy_household):
    # Mirrors chores/migrations/0008_fairnessweights.backfill_fairness_weights.
    for household in Household.objects.filter(fairness_weights__isnull=True):
        FairnessWeights.objects.create(household=household)

    legacy_household.refresh_from_db()
    assert legacy_household.fairness_weights.time_weight == DEFAULT_TIME_WEIGHT


@pytest.mark.django_db
def test_signal_is_idempotent_for_an_existing_row(nest):
    nest.save()  # a second post_save
    assert FairnessWeights.objects.filter(household=nest).count() == 1


# --- the edit view -------------------------------------------------


@pytest.mark.django_db
def test_get_shows_current_values_to_a_member(client, signed_in_alice, nest, edit_url):
    nest.fairness_weights.time_weight = 0.7
    nest.fairness_weights.save()

    response = client.get(edit_url)
    assert response.status_code == 200
    assert b'name="time_weight"' in response.content
    assert b"0.7" in response.content


@pytest.mark.django_db
def test_anonymous_visitor_is_redirected_to_login(client, edit_url):
    response = client.get(edit_url)
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_user_with_no_household_is_redirected_to_onboarding(client, alice, edit_url):
    client.login(username="alice", password=GOOD_PASSWORD)
    response = client.get(edit_url)
    assert response.status_code == 302
    assert response.url == reverse("chores:household_create")


@pytest.mark.django_db
def test_valid_post_updates_the_row_and_reports_success(
    client, signed_in_alice, nest, edit_url
):
    response = client.post(
        edit_url,
        {
            "time_weight": "0.5",
            "difficulty_weight": "2.0",
            "decay_half_life_days": "45",
        },
        follow=True,
    )
    assert response.status_code == 200
    assert any("updated" in str(m) for m in response.context["messages"])

    weights = nest.fairness_weights
    weights.refresh_from_db()
    assert weights.time_weight == 0.5
    assert weights.difficulty_weight == 2.0
    assert weights.decay_half_life_days == 45


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {"time_weight": "0.5", "difficulty_weight": "1.0", "decay_half_life_days": "0"},
        {"time_weight": "0.5", "difficulty_weight": "1.0", "decay_half_life_days": "-3"},
        {"time_weight": "-1", "difficulty_weight": "1.0", "decay_half_life_days": "30"},
        {"time_weight": "1.0", "difficulty_weight": "999", "decay_half_life_days": "30"},
    ],
)
def test_invalid_post_is_rejected_and_changes_nothing(
    client, signed_in_alice, nest, edit_url, payload
):
    before = nest.fairness_weights
    response = client.post(edit_url, payload)
    assert response.status_code == 200

    after = FairnessWeights.objects.get(household=nest)
    assert after.time_weight == before.time_weight
    assert after.difficulty_weight == before.difficulty_weight
    assert after.decay_half_life_days == before.decay_half_life_days


# --- model-level validation --------------------------------------


@pytest.mark.django_db
def test_model_full_clean_rejects_out_of_range_values(nest):
    weights = nest.fairness_weights
    weights.decay_half_life_days = 0
    with pytest.raises(ValidationError):
        weights.full_clean()

    weights = FairnessWeights.objects.get(household=nest)
    weights.difficulty_weight = 50
    with pytest.raises(ValidationError):
        weights.full_clean()


@pytest.mark.django_db
def test_nav_shows_fairness_link_for_a_member(client, signed_in_alice, edit_url):
    body = client.get(reverse("chores:home")).content.decode()
    assert edit_url in body
