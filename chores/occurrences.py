"""Occurrence date math and generation.

``occurrence_dates`` is pure ``datetime.date`` arithmetic and imports nothing
from Django, so it is unit-tested in isolation. ``generate_occurrences`` may
touch the ORM to create rows.
"""

from datetime import date, timedelta

from django.utils import timezone

from .models import ChoreOccurrence, OCCURRENCE_STATUS_ACTIVE


def occurrence_dates(anchor: date, cadence_days: int, through: date) -> list[date]:
    """Return ``[anchor, anchor + cadence_days, ...]`` up to and including
    ``through``.

    Returns an empty list when ``anchor > through``. Takes and returns plain
    ``datetime.date`` values.
    """
    dates: list[date] = []
    current = anchor
    step = timedelta(days=cadence_days)
    while current <= through:
        dates.append(current)
        current += step
    return dates


def generate_occurrences(chore, through: date) -> list[ChoreOccurrence]:
    """Create the missing occurrences for ``chore`` up to and including
    ``through``.

    The grid is anchored at ``timezone.localdate(chore.created_at)`` and spaced
    by ``chore.cadence_days``. Dates on or before the chore's latest existing
    occurrence are skipped, as is any date that already has a row. Returns the
    list of created objects (empty when nothing was created). Idempotent.
    """
    anchor = timezone.localdate(chore.created_at)
    grid = occurrence_dates(anchor, chore.cadence_days, through)
    if not grid:
        return []

    existing = set(
        chore.occurrences.values_list("due_date", flat=True)
    )
    latest_existing = max(existing) if existing else None

    to_create = [
        d
        for d in grid
        if (latest_existing is None or d > latest_existing) and d not in existing
    ]
    if not to_create:
        return []

    return ChoreOccurrence.objects.bulk_create(
        [
            ChoreOccurrence(
                chore=chore,
                due_date=d,
                status=OCCURRENCE_STATUS_ACTIVE,
            )
            for d in to_create
        ]
    )
