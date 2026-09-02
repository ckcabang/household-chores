"""Occurrence date math, generation, overdue derivation, and the command."""

from datetime import date, datetime, timedelta, timezone as dt_timezone
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from chores.models import (
    Chore,
    ChoreOccurrence,
    Household,
    OCCURRENCE_STATUS_ACTIVE,
    OCCURRENCE_STATUS_COMPLETED,
)
from chores.occurrences import generate_occurrences, occurrence_dates


# --- pure helper: occurrence_dates ----------------------------------


def test_occurrence_dates_spacing():
    anchor = date(2026, 1, 1)
    assert occurrence_dates(anchor, 3, date(2026, 1, 10)) == [
        date(2026, 1, 1),
        date(2026, 1, 4),
        date(2026, 1, 7),
        date(2026, 1, 10),
    ]


def test_occurrence_dates_includes_through_only_when_on_grid():
    anchor = date(2026, 1, 1)
    # through falls between grid points -> last point is the one before it
    assert occurrence_dates(anchor, 5, date(2026, 1, 9)) == [
        date(2026, 1, 1),
        date(2026, 1, 6),
    ]


def test_occurrence_dates_empty_when_anchor_after_through():
    assert occurrence_dates(date(2026, 2, 1), 7, date(2026, 1, 1)) == []


# --- fixtures -------------------------------------------------------


@pytest.fixture
def household(db):
    return Household.objects.create(name="The Nest")


def make_chore(household, *, created_on, cadence_days):
    chore = Chore.objects.create(
        household=household,
        name="Dishes",
        cadence_days=cadence_days,
        estimated_minutes=10,
        difficulty=3,
    )
    # created_at is auto_now_add; pin it so the grid anchor is deterministic.
    aware = datetime(
        created_on.year, created_on.month, created_on.day, 12, 0,
        tzinfo=dt_timezone.utc,
    )
    Chore.objects.filter(pk=chore.pk).update(created_at=aware)
    chore.refresh_from_db()
    return chore


# --- generate_occurrences -----------------------------------------


@pytest.mark.django_db
def test_first_run_created_count(household):
    chore = make_chore(household, created_on=date(2026, 1, 1), cadence_days=2)
    created = generate_occurrences(chore, date(2026, 1, 11))
    # 2026-01-01, 03, 05, 07, 09, 11 -> 6 dates
    assert len(created) == 6
    assert chore.occurrences.count() == 6


@pytest.mark.django_db
def test_idempotent_rerun(household):
    chore = make_chore(household, created_on=date(2026, 1, 1), cadence_days=2)
    through = date(2026, 1, 11)
    generate_occurrences(chore, through)
    created_again = generate_occurrences(chore, through)
    assert created_again == []
    assert chore.occurrences.count() == 6


@pytest.mark.django_db
def test_generated_due_dates_follow_cadence_spacing(household):
    chore = make_chore(household, created_on=date(2026, 1, 1), cadence_days=5)
    generate_occurrences(chore, date(2026, 1, 31))
    due = list(chore.occurrences.order_by("due_date").values_list("due_date", flat=True))
    assert due == [
        date(2026, 1, 1),
        date(2026, 1, 6),
        date(2026, 1, 11),
        date(2026, 1, 16),
        date(2026, 1, 21),
        date(2026, 1, 26),
        date(2026, 1, 31),
    ]


@pytest.mark.django_db
def test_second_run_extends_window_without_duplicates(household):
    chore = make_chore(household, created_on=date(2026, 1, 1), cadence_days=2)
    generate_occurrences(chore, date(2026, 1, 5))  # 01, 03, 05
    created = generate_occurrences(chore, date(2026, 1, 9))  # 07, 09
    assert [o.due_date for o in created] == [date(2026, 1, 7), date(2026, 1, 9)]
    assert chore.occurrences.count() == 5


# --- is_overdue derivation ---------------------------------------


@pytest.mark.django_db
def test_is_overdue_true_for_past_active(household):
    chore = make_chore(household, created_on=date(2026, 1, 1), cadence_days=1)
    occ = ChoreOccurrence.objects.create(
        chore=chore,
        due_date=timezone.localdate() - timedelta(days=1),
        status=OCCURRENCE_STATUS_ACTIVE,
    )
    assert occ.is_overdue is True


@pytest.mark.django_db
def test_is_overdue_false_for_future_active(household):
    chore = make_chore(household, created_on=date(2026, 1, 1), cadence_days=1)
    occ = ChoreOccurrence.objects.create(
        chore=chore,
        due_date=timezone.localdate() + timedelta(days=1),
        status=OCCURRENCE_STATUS_ACTIVE,
    )
    assert occ.is_overdue is False


@pytest.mark.django_db
def test_is_overdue_false_for_past_completed(household):
    chore = make_chore(household, created_on=date(2026, 1, 1), cadence_days=1)
    occ = ChoreOccurrence.objects.create(
        chore=chore,
        due_date=timezone.localdate() - timedelta(days=1),
        status=OCCURRENCE_STATUS_COMPLETED,
    )
    assert occ.is_overdue is False


# --- management command ----------------------------------------


@pytest.mark.django_db
def test_command_runs_cleanly_on_empty_database():
    out = StringIO()
    call_command("generate_occurrences", stdout=out)
    assert "Created 0 occurrence(s)." in out.getvalue()
    assert ChoreOccurrence.objects.count() == 0


@pytest.mark.django_db
def test_command_generates_for_every_chore(household):
    other = Household.objects.create(name="Next door")
    make_chore(household, created_on=timezone.localdate(), cadence_days=7)
    make_chore(other, created_on=timezone.localdate(), cadence_days=7)

    out = StringIO()
    call_command("generate_occurrences", "--days", "14", stdout=out)

    # each chore: today, +7, +14 -> 3 occurrences
    assert ChoreOccurrence.objects.count() == 6
    assert "Created 6 occurrence(s)." in out.getvalue()


@pytest.mark.django_db
def test_command_default_window_is_30_days(household):
    make_chore(household, created_on=timezone.localdate(), cadence_days=10)
    call_command("generate_occurrences", stdout=StringIO())
    # today, +10, +20, +30 -> 4
    assert household.chores.get().occurrences.count() == 4
