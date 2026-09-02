# Chore management

## Goal

Either household member can list, create, edit, and delete their
household's chores through templated forms.

## Acceptance criteria

- [ ] `Chore` model: FK `household`, `name`, `description` (blank allowed),
      `cadence_days` (positive int), `estimated_minutes` (positive int),
      `difficulty` (small int on a fixed scale defined once as a choices
      constant, e.g. 1–5), nullable FK `primary_owner` → `Membership`,
      `allows_multiple_contributors` (bool, default `False`), `created_at` /
      `updated_at`.
- [ ] `primary_owner`, when set, must be a membership of the same household —
      validated in `clean()` and covered by a test.
- [ ] `GET /chores/` lists the current household's chores (name, cadence,
      estimate, difficulty, owner). Chores of other households never appear.
- [ ] `GET`/`POST` for `/chores/new/`, `/chores/<id>/edit/`, and
      `/chores/<id>/delete/` (POST-confirmed) all work and are scoped to the
      user's household; targeting a chore outside the household returns 404.
- [ ] Invalid input (blank name, non-positive cadence or estimate, difficulty
      out of range) re-renders the form with field errors and saves nothing.
- [ ] Every chore view requires login and household membership; a user with no
      household is redirected to onboarding (`/household/new/`).
- [ ] `Chore` is registered in the admin with `list_display` and a household
      filter.
- [ ] Tests cover: list scoping, create, edit, delete, validation failure,
      cross-household 404.

## Out of scope

- Generating occurrences from the cadence — task #9.
- People ↔ chore prefer / exclude constraints — task #8.
- Re-spacing already-generated occurrences when a chore's cadence changes —
  follow-up: [#27](https://github.com/ckcabang/household-chores/issues/27) (Reconcile occurrences when cadence changes).
- Archive / pause / soft-delete and any richer lifecycle — permanently excluded
  (`_docs/plan.md`).

## Constraints

- Model in `chores/models.py`; the difficulty scale is a single choices
  constant reused by forms, the fairness module, and task #10's effort field.
- Class-based views (`ListView` / `CreateView` / `UpdateView` / `DeleteView`)
  with a shared household-scoping mixin; templates extend `chores/base.html`.
- Add the "Chores" link to the nav in `base.html`.
