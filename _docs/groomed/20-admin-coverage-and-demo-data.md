# Admin coverage and demo data

## Goal

Every model has a useful Django admin registration, and one management
command builds a complete demo household for local testing and
screenshots.

## Acceptance criteria

- [ ] Every model in `chores/models.py` is registered in `chores/admin.py` with
      a meaningful `list_display`, plus `list_filter` / `search_fields` /
      `date_hierarchy` where they help.
- [ ] `uv run python manage.py check` passes, and each model's changelist and
      add form load without error (smoke-tested).
- [ ] `manage.py seed_demo [--reset]` creates: two users with documented
      credentials, a household with both memberships, a `FairnessWeights` row,
      several chores of varying cadence and difficulty, generated occurrences
      spanning past and future, and completions plus at least one contribution
      credit in the history.
- [ ] Running with `--reset` clears prior demo data first; running twice without
      `--reset` fails with a clear message rather than duplicating.
- [ ] After seeding, the dashboard renders with a non-empty balance and history.
- [ ] A test runs `seed_demo` on an empty database and asserts the expected
      object counts, and checks that a second run without `--reset` is handled.

## Out of scope

- Production seed data or fixtures — the demo data is for local use and
  screenshots only.
- Adopting a factory library (`factory_boy` etc.) across the test suite —
  revisit only if tests need it broadly.

## Constraints

- Command at `chores/management/commands/seed_demo.py`; the demo user
  credentials are documented in the README.
- The command refuses to run when `DEBUG` is `False` unless passed `--force`.
- Reuse `generate_occurrences` from task #9 rather than hand-building
  occurrences.
