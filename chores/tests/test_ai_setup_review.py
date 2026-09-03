"""AI setup review + apply: /setup/review/ and chores.ai.apply.apply_draft."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from chores.ai.apply import apply_draft
from chores.models import (
    AISetupDraft,
    Chore,
    Constraint,
    Household,
    Membership,
)

User = get_user_model()
PW = "correct-horse-7"


PLAN = {
    "chores": [
        {"name": "Dishes", "cadence_days": 1, "estimated_minutes": 15, "difficulty": 2},
        {"name": "Vacuum", "cadence_days": 7, "estimated_minutes": 30, "difficulty": 3},
    ],
    "constraints": [
        {"person": "alice", "chore": "Dishes", "kind": "prefer"},
        {"person": "ghost", "chore": "Dishes", "kind": "exclude"},
    ],
    "assignments": [
        {"chore": "Dishes", "member": "alice"},
        {"chore": "Vacuum", "member": "bob"},
        {"chore": "Nonexistent", "member": "bob"},
    ],
    "reasoning": "Split roughly evenly.",
}


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


@pytest.fixture
def draft(nest):
    return AISetupDraft.objects.create(
        household=nest,
        raw_response=PLAN,
        chores=PLAN["chores"],
        constraints=PLAN["constraints"],
        assignments=PLAN["assignments"],
        reasoning=PLAN["reasoning"],
    )


@pytest.fixture
def review_url():
    return reverse("chores:setup_review")


# --- apply_draft (unit) --------------------------------------


@pytest.mark.django_db
def test_apply_draft_creates_chores_constraints_and_flags_assignments(
    nest, alice_m, bob_m, draft
):
    counts = apply_draft(draft)

    assert counts["chores"] == 2
    assert Chore.objects.filter(household=nest).count() == 2

    dishes = Chore.objects.get(name="Dishes")
    assert dishes.primary_owner == alice_m
    assert dishes.assignment_needs_review is True

    vacuum = Chore.objects.get(name="Vacuum")
    assert vacuum.primary_owner == bob_m

    # Only the resolvable constraint is created (the "ghost" person is skipped).
    assert Constraint.objects.count() == 1
    constraint = Constraint.objects.get()
    assert constraint.membership == alice_m
    assert constraint.kind == "prefer"

    draft.refresh_from_db()
    assert draft.status == "applied"
    assert draft.applied_at is not None


@pytest.mark.django_db
def test_apply_draft_is_atomic_on_a_bad_chore(nest, alice_m, bob_m):
    bad = AISetupDraft.objects.create(
        household=nest,
        raw_response={},
        chores=[
            {"name": "Good", "cadence_days": 2, "estimated_minutes": 10, "difficulty": 3},
            {"name": "", "cadence_days": 2, "estimated_minutes": 10, "difficulty": 3},
        ],
        constraints=[],
        assignments=[],
    )
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        apply_draft(bad)

    assert Chore.objects.count() == 0
    bad.refresh_from_db()
    assert bad.status == "draft"


# --- the review view ---------------------------------------


@pytest.mark.django_db
def test_get_renders_the_draft(client, as_alice, bob_m, draft, review_url):
    body = client.get(review_url).content.decode()
    assert "Dishes" in body and "Vacuum" in body
    assert "Split roughly evenly" in body
    assert 'name="chore-0-name"' in body


@pytest.mark.django_db
def test_no_draft_redirects_to_setup(client, as_alice, review_url):
    response = client.get(review_url)
    assert response.status_code == 302
    assert response.url == reverse("chores:setup")


@pytest.mark.django_db
def test_edits_persist_to_the_draft(client, as_alice, bob_m, draft, review_url):
    client.post(
        review_url,
        {
            "action": "save",
            "chore-0-name": "Wash up",
            "chore-0-cadence_days": "2",
            "chore-0-estimated_minutes": "20",
            "chore-0-difficulty": "3",
            "chore-1-name": "Vacuum",
            "chore-1-cadence_days": "7",
            "chore-1-estimated_minutes": "30",
            "chore-1-difficulty": "3",
            "chore-1-remove": "on",
            "constraint-0-person": "alice",
            "constraint-0-chore": "Dishes",
            "constraint-0-kind": "prefer",
            "constraint-1-person": "ghost",
            "constraint-1-chore": "Dishes",
            "constraint-1-kind": "exclude",
        },
    )
    draft.refresh_from_db()
    assert [c["name"] for c in draft.chores] == ["Wash up"]
    assert draft.chores[0]["cadence_days"] == 2
    assert len(draft.constraints) == 2  # neither removed


@pytest.mark.django_db
def test_confirm_creates_records_and_redirects_to_dashboard(
    client, as_alice, bob_m, draft, review_url
):
    response = client.post(
        review_url,
        {
            "action": "confirm",
            "chore-0-name": "Dishes",
            "chore-0-cadence_days": "1",
            "chore-0-estimated_minutes": "15",
            "chore-0-difficulty": "2",
            "chore-1-name": "Vacuum",
            "chore-1-cadence_days": "7",
            "chore-1-estimated_minutes": "30",
            "chore-1-difficulty": "3",
            "constraint-0-person": "alice",
            "constraint-0-chore": "Dishes",
            "constraint-0-kind": "prefer",
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("chores:dashboard")
    assert Chore.objects.count() == 2
    assert Constraint.objects.count() == 1
    draft.refresh_from_db()
    assert draft.status == "applied"


@pytest.mark.django_db
def test_double_confirm_does_not_double_create(
    client, as_alice, bob_m, draft, review_url
):
    apply_draft(draft)
    before = Chore.objects.count()

    response = client.post(review_url, {"action": "confirm"}, follow=True)
    assert Chore.objects.count() == before
    assert any("already been applied" in str(m) for m in response.context["messages"])
    assert response.redirect_chain[-1][0] == reverse("chores:dashboard")


@pytest.mark.django_db
def test_invalid_edit_on_confirm_shows_a_message_and_creates_nothing(
    client, as_alice, bob_m, draft, review_url
):
    response = client.post(
        review_url,
        {
            "action": "confirm",
            "chore-0-name": "",
            "chore-0-cadence_days": "1",
            "chore-0-estimated_minutes": "15",
            "chore-0-difficulty": "2",
        },
    )
    assert response.status_code == 200
    assert Chore.objects.count() == 0
    assert any("invalid" in str(m).lower() for m in response.context["messages"])


@pytest.mark.django_db
def test_anonymous_is_redirected_to_login(client, review_url):
    response = client.get(review_url)
    assert response.status_code == 302
    assert reverse("login") in response.url
