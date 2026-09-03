"""App-layer glue that turns fairness suggestions into stored proposals."""

from .fairness import propose_estimate
from .models import (
    PROPOSAL_STATUS_PENDING,
    Completion,
    EstimateProposal,
)


def _actual_minutes_for(chore):
    """A chore's logged ``actual_minutes``, oldest completion first."""
    return list(
        Completion.objects.filter(occurrence__chore=chore)
        .order_by("occurrence__completed_at", "id")
        .values_list("actual_minutes", flat=True)
    )


def generate_estimate_proposals(household):
    """Create ``pending`` :class:`EstimateProposal` rows for a household.

    Runs :func:`chores.fairness.propose_estimate` over each chore's logged
    times. Skips a chore that already has a pending proposal. Returns the list
    of proposals created.
    """
    created = []
    chores_with_pending = set(
        EstimateProposal.objects.filter(
            chore__household=household, status=PROPOSAL_STATUS_PENDING
        ).values_list("chore_id", flat=True)
    )
    for chore in household.chores.all():
        if chore.id in chores_with_pending:
            continue
        suggestion = propose_estimate(
            chore.estimated_minutes, _actual_minutes_for(chore)
        )
        if suggestion is None:
            continue
        created.append(
            EstimateProposal.objects.create(
                chore=chore,
                proposed_minutes=suggestion.proposed_minutes,
                rationale=suggestion.rationale,
            )
        )
    return created
