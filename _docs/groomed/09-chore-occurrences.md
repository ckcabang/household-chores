# Chore occurrences

## Goal

A pure date-math function and a management command generate the missing
dated occurrences for each chore across a forward date window from its
cadence. Overdue is never stored — it is derived on read.

## Acceptance criteria

- [ ] `ChoreOccurrence` model in `chores/models.py`, with a migration: FK
      `chore` (`related_name="occurrences"`), `due_date` (date), `status`
      (`active` | `completed`, default `active`, from a module-level
      `OCCURRENCE_STATUS_CHOICES` list of `(value, label)` pairs mirroring the
      existing `*_CHOICES` constants), nullable `completed_at` (datetime,
      written later by task #10, not by this task).
- [ ] `UniqueConstraint` on (`chore`, `due_date`), named e.g.
      `unique_occurrence_per_chore_per_date`.
- [ ] A pure helper `occurrence_dates(anchor, cadence_days, through)` in
      `chores/occurrences.py` returns the ascending list of `date`s
      `anchor, anchor + cadence_days, anchor + 2*cadence_days, …` up to and
      including `through` (empty when `anchor > through`). It takes and returns
      plain `datetime.date` values and imports nothing from Django, so it is
      unit-tested in isolation.
- [ ] `generate_occurrences(chore, through)` in `chores/occurrences.py`:
      - `through` is a `date` (the last day to generate up to, inclusive).
      - The grid anchor is `timezone.localdate(chore.created_at)`.
      - It builds the full grid via `occurrence_dates(anchor, chore.cadence_days,
        through)`, drops any date `<=` the chore's latest existing
        `due_date` (keeps the whole grid when the chore has none), and drops any
        date that already has a row (the `UniqueConstraint` is the backstop).
      - It bulk-creates the remaining occurrences as `active` and returns the
        list of created objects (empty list when nothing was created).
      - The module may import Django models; only `occurrence_dates` must stay
        Django-free.
- [ ] Calling `generate_occurrences(chore, through)` twice with the same
      `through` creates nothing the second time (idempotent) — covered by a
      test.
- [ ] `manage.py generate_occurrences [--days N]` iterates every chore of every
      household and calls `generate_occurrences(chore, timezone.localdate() +
      timedelta(days=N))`. `--days` defaults to `30`. The whole run is wrapped
      in one `transaction.atomic` block. It prints the total number of
      occurrences created (and exits 0 when that is zero).
- [ ] No `overdue` field exists anywhere. `ChoreOccurrence.is_overdue` (a
      property) returns `True` for an `active` occurrence whose `due_date` is
      strictly before `timezone.localdate()`, and `False` otherwise (including
      for any `completed` occurrence).
- [ ] `ChoreOccurrence` is registered in `chores/admin.py` with a
      `list_display` covering chore, due date and status, and a `status` /
      `chore__household` `list_filter`.
- [ ] Tests in `chores/tests/` cover: `occurrence_dates` spacing in isolation,
      first-run created count for a chore, idempotent re-run (0 created),
      cadence spacing of the generated `due_date`s, `is_overdue` derivation
      (past active True, future active False, past completed False), and
      `manage.py generate_occurrences` running cleanly on an empty database.
- [ ] `uv run pytest` and `uv run python manage.py check` pass.

## Out of scope

- Scheduling the command (cron / worker) — the MVP runs it manually;
  `_docs/tech-stack-decision.md` rules out required background jobs.
- Re-spacing or removing future occurrences when a chore's cadence changes —
  follow-up: [#27](https://github.com/ckcabang/household-chores/issues/27) (Reconcile occurrences when cadence changes) (shared with
  task #7).
- Completing an occurrence and the `completed_at` write — task #10.
- Displaying occurrences — task #17.

## Constraints

- Date math (`occurrence_dates`) and `generate_occurrences` live in
  `chores/occurrences.py`, imported by the command; the command file is at
  `chores/management/commands/generate_occurrences.py` (add
  `chores/management/__init__.py` and `chores/management/commands/__init__.py`).
- Use `timezone.localdate()` for "today" and `timezone.localdate(dt)` to reduce
  a stored datetime to a local date; respect `USE_TZ` (already `True`).
- `Chore.cadence_days` is already a `PositiveIntegerField` with
  `MinValueValidator(1)` (task #7), so it is always `>= 1` — no extra guard or
  upper cap is needed; a large cadence simply yields few or no dates.
- No new dependencies.
