"""Adapters from ORM rows to the plain inputs ``chores.fairness`` expects.

Views and commands call these; the fairness package itself stays Django-free.
"""

from datetime import timedelta

from django.db.models import Count

from .fairness import AssignableChore, WorkItem, member_workloads, workload_value
from .models import (
    OCCURRENCE_STATUS_ACTIVE,
    Completion,
    Constraint,
    ContributionCredit,
    FairnessWeights,
)

# How far back completed work counts toward the current fairness balance. The
# decay half-life (default 30 days) already fades older items; 90 days keeps a
# couple of half-lives of history in view.
BALANCE_WINDOW_DAYS = 90

# The dashboard's plain-count "recent contribution" summary looks back this far.
HISTORY_WINDOW_DAYS = 30


def household_params(household):
    weights, _ = FairnessWeights.objects.get_or_create(household=household)
    return weights.as_params()


def _completion_items(household, since):
    completions = (
        Completion.objects.filter(
            occurrence__chore__household=household,
            occurrence__completed_at__gte=since,
        )
        .select_related("occurrence__chore", "credit")
    )
    for completion in completions:
        chore = completion.occurrence.chore
        yield WorkItem(
            actor_id=completion.completed_by_id,
            owner_id=chore.primary_owner_id,
            timestamp=completion.occurrence.completed_at,
            minutes=chore.estimated_minutes,
            effort=chore.difficulty,
            credited=hasattr(completion, "credit"),
        )


def household_workloads(household, now, window_days=BALANCE_WINDOW_DAYS):
    """Each member's decayed workload over the trailing ``window_days``."""
    member_ids = list(household.memberships.values_list("id", flat=True))
    since = now - timedelta(days=window_days)
    items = list(_completion_items(household, since))
    return member_workloads(items, member_ids, household_params(household), now)


def assignable_chores(household, params=None):
    """Chores with at least one active occurrence, as ``AssignableChore`` data."""
    params = params or household_params(household)
    chores = household.chores.filter(
        occurrences__status=OCCURRENCE_STATUS_ACTIVE
    ).distinct()
    return [
        AssignableChore(
            id=chore.id,
            cost=workload_value(chore.estimated_minutes, chore.difficulty, params),
            owner_id=chore.primary_owner_id,
        )
        for chore in chores
    ]


def household_constraints(household):
    """``(member_id, chore_id, kind)`` triples for the assignment function."""
    return list(
        Constraint.objects.filter(chore__household=household).values_list(
            "membership_id", "chore_id", "kind"
        )
    )


def recent_contribution(household, now, window_days=HISTORY_WINDOW_DAYS):
    """Plain counts per member over the trailing window: completions and the
    contribution credits they earned by helping.

    Returns ``{membership_id: {"completions": int, "credits": int}}``.
    """
    since = now - timedelta(days=window_days)
    summary = {
        mid: {"completions": 0, "credits": 0}
        for mid in household.memberships.values_list("id", flat=True)
    }

    completions = (
        Completion.objects.filter(
            occurrence__chore__household=household,
            occurrence__completed_at__gte=since,
        )
        .values("completed_by_id")
        .annotate(n=Count("id"))
    )
    for row in completions:
        if row["completed_by_id"] in summary:
            summary[row["completed_by_id"]]["completions"] = row["n"]

    credits = (
        ContributionCredit.objects.filter(
            helper__household=household, created_at__gte=since
        )
        .values("helper_id")
        .annotate(n=Count("id"))
    )
    for row in credits:
        if row["helper_id"] in summary:
            summary[row["helper_id"]]["credits"] = row["n"]

    return summary
