# Chore occurrences

## Goal

A function and a management command generate the missing dated
occurrences for each chore across a date window from its cadence.
Overdue is never stored — it is derived on read.

## Acceptance criteria

- [ ] `ChoreOccurrence` model: FK `chore`, `due_date` (date), `status`
      (`active` | `completed`, default `active`), nullable `completed_at`
      (datetime).
- [ ] `UniqueConstraint` on (`chore`, `due_date`).
- [ ] `generate_occurrences(chore, start, end)` in a plain module creates
      occurrences at `cadence_days` spacing, starting from the day after the
      chore's latest existing occurrence (or the chore's creation date when
      none exist), up to and including `end`; it skips dates that already exist
      and returns the created objects.
- [ ] Calling it twice for the same window creates nothing the second time
      (idempotent) — covered by a test.
- [ ] `manage.py generate_occurrences [--days N]` runs generation for every
      chore in every household over the next `N` days (default documented, e.g.
      30) and reports how many were created.
- [ ] No `overdue` field exists. `ChoreOccurrence.is_overdue` (or a queryset
      method) returns `True` for an `active` occurrence whose `due_date` is
      before `timezone.localdate()`.
- [ ] Tests cover: first-run count, idempotent re-run, cadence spacing, overdue
      derivation, and the command running cleanly on an empty database.

## Out of scope

- Scheduling the command (cron / worker) — the MVP runs it manually;
  `_docs/tech-stack-decision.md` rules out required background jobs.
- Re-spacing or removing future occurrences when a chore's cadence changes —
  follow-up: [#27](https://github.com/ckcabang/household-chores/issues/27) (Reconcile occurrences when cadence changes) (shared with
  task #7).
- Completing an occurrence — task #10.
- Displaying occurrences — task #17.

## Constraints

- Generation logic in a framework-light module (e.g. `chores/occurrences.py`)
  imported by the command, so the date math is testable in isolation.
- Use `timezone.localdate()` for "today" and respect `USE_TZ`.
- Command file at `chores/management/commands/generate_occurrences.py`.
