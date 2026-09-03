"""Turn a reviewed :class:`AISetupDraft` into real Chore and Constraint rows.

All-or-nothing: everything happens in one ``transaction.atomic`` block, so a
validation failure part-way through leaves the household untouched and the
draft still a draft.
"""

from django.db import transaction
from django.utils import timezone

from ..models import AI_DRAFT_STATUS_APPLIED, Chore, Constraint


def _norm(value):
    return str(value or "").strip().lower()


def apply_draft(draft):
    """Create chores/constraints from ``draft`` and mark it applied.

    Assignments are recorded on the chore's ``primary_owner`` with
    ``assignment_needs_review=True`` - never treated as final. Entries whose
    chore or member name can't be resolved are skipped. Returns a small counts
    dict.
    """
    household = draft.household
    members = {
        _norm(m.user.username): m
        for m in household.memberships.select_related("user")
    }

    with transaction.atomic():
        chores_by_name = {}
        for entry in draft.chores or []:
            chore = Chore(
                household=household,
                name=str(entry.get("name", "")).strip(),
                cadence_days=int(entry.get("cadence_days") or 0),
                estimated_minutes=int(entry.get("estimated_minutes") or 0),
                difficulty=int(entry.get("difficulty") or 0),
            )
            chore.full_clean()
            chore.save()
            chores_by_name[_norm(chore.name)] = chore

        assignments_flagged = 0
        for entry in draft.assignments or []:
            chore = chores_by_name.get(_norm(entry.get("chore")))
            member = members.get(_norm(entry.get("member")))
            if chore is None or member is None:
                continue
            chore.primary_owner = member
            chore.assignment_needs_review = True
            chore.full_clean()
            chore.save(
                update_fields=["primary_owner", "assignment_needs_review", "updated_at"]
            )
            assignments_flagged += 1

        constraints_created = 0
        for entry in draft.constraints or []:
            chore = chores_by_name.get(_norm(entry.get("chore")))
            member = members.get(_norm(entry.get("person")))
            kind = entry.get("kind")
            if chore is None or member is None or kind not in ("prefer", "exclude"):
                continue
            if Constraint.objects.filter(chore=chore, membership=member).exists():
                continue
            constraint = Constraint(chore=chore, membership=member, kind=kind)
            constraint.full_clean()
            constraint.save()
            constraints_created += 1

        draft.status = AI_DRAFT_STATUS_APPLIED
        draft.applied_at = timezone.now()
        draft.save(update_fields=["status", "applied_at"])

    return {
        "chores": len(chores_by_name),
        "assignments_flagged": assignments_flagged,
        "constraints": constraints_created,
    }
