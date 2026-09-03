"""The seed_demo command and admin changelist/add smoke tests."""

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse

from chores.models import (
    Chore,
    ChoreOccurrence,
    ContributionCredit,
    Household,
    Membership,
)

User = get_user_model()


@pytest.fixture
def debug_on(settings):
    """The test runner forces DEBUG=False; seed_demo needs it on."""
    settings.DEBUG = True


# --- seed_demo -------------------------------------------------


@pytest.mark.django_db
def test_seed_demo_builds_a_complete_household(debug_on, capsys):
    call_command("seed_demo")

    household = Household.objects.get(name="Demo Household")
    assert Membership.objects.filter(household=household).count() == 2
    assert User.objects.filter(username__in=["demo-alice", "demo-bob"]).count() == 2
    assert household.fairness_weights is not None
    assert Chore.objects.filter(household=household).count() == 6

    occurrences = ChoreOccurrence.objects.filter(chore__household=household)
    assert occurrences.count() > 0
    assert occurrences.filter(status="completed").exists()
    assert occurrences.filter(status="active").exists()
    assert ContributionCredit.objects.filter(helper__household=household).exists()


@pytest.mark.django_db
def test_second_run_without_reset_fails_and_does_not_duplicate(debug_on):
    call_command("seed_demo")
    chores_before = Chore.objects.count()

    with pytest.raises(CommandError):
        call_command("seed_demo")

    assert Chore.objects.count() == chores_before
    assert Household.objects.filter(name="Demo Household").count() == 1


@pytest.mark.django_db
def test_reset_rebuilds_cleanly(debug_on):
    call_command("seed_demo")
    first_ids = set(Chore.objects.values_list("id", flat=True))

    call_command("seed_demo", "--reset")

    assert Household.objects.filter(name="Demo Household").count() == 1
    assert Chore.objects.filter(household__name="Demo Household").count() == 6
    assert first_ids.isdisjoint(set(Chore.objects.values_list("id", flat=True)))


@pytest.mark.django_db
def test_refuses_when_debug_is_false(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_demo")
    assert not Household.objects.filter(name="Demo Household").exists()


@pytest.mark.django_db
def test_force_runs_with_debug_false(settings):
    settings.DEBUG = False
    call_command("seed_demo", "--force")
    assert Household.objects.filter(name="Demo Household").exists()


@pytest.mark.django_db
def test_dashboard_renders_with_seeded_data(debug_on, client):
    call_command("seed_demo")
    client.login(username="demo-alice", password="demo-pass-alice")
    response = client.get(reverse("chores:dashboard"))
    assert response.status_code == 200
    balance = {row["member"].user.username: row["workload"] for row in response.context["balance"]}
    assert any(v > 0 for v in balance.values())


# --- admin smoke ---------------------------------------------


CHORES_MODELS = [
    m for m in apps.get_app_config("chores").get_models()
]


@pytest.mark.django_db
@pytest.mark.parametrize("model", CHORES_MODELS, ids=lambda m: m.__name__)
def test_admin_changelist_and_add_load(admin_client, model):
    meta = model._meta
    changelist = reverse(f"admin:{meta.app_label}_{meta.model_name}_changelist")
    add = reverse(f"admin:{meta.app_label}_{meta.model_name}_add")

    assert admin_client.get(changelist).status_code == 200
    assert admin_client.get(add).status_code == 200
