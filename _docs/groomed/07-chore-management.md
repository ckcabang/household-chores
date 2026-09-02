# Chore management

## Goal

Either household member can list, create, edit, and delete their
household's chores through templated forms.

## Acceptance criteria

- [ ] `Chore` model in `chores/models.py`, with a migration: FK `household`,
      `name`, `description` (blank allowed), `cadence_days` (positive int),
      `estimated_minutes` (positive int), `difficulty` (small int on a fixed
      scale), nullable FK `primary_owner` → `Membership`,
      `allows_multiple_contributors` (bool, default `False`), `created_at` /
      `updated_at`.
- [ ] The difficulty scale is defined once as a module-level constant
      `DIFFICULTY_CHOICES` (a list of `(value, label)` pairs, e.g. 1–5) in
      `chores/models.py`, used as the field's `choices=`. Forms, the fairness
      module, and task #10's effort field import this constant rather than
      redefining the range.
- [ ] `primary_owner`, when set, must be a membership of the same household —
      validated in `Chore.clean()` and covered by a test.
- [ ] A shared household-scoping mixin is introduced by this task —
      `HouseholdScopedMixin` in `chores/views.py` — that: requires login,
      redirects a signed-in user with no `Membership` to `chores:household_create`
      (on both GET and POST), exposes the current `Household`/`Membership` to the
      view, and filters the view's queryset to `household=<current household>`.
      Later tasks (#8, #10, #14, #17) reuse it rather than re-deriving the
      household per view.
- [ ] `GET /chores/` (URL name `chores:chore_list`) lists the current
      household's chores (name, cadence, estimate, difficulty, owner). Chores of
      other households never appear.
- [ ] `GET`/`POST` for `chores:chore_create` at `/chores/new/`,
      `chores:chore_edit` at `/chores/<int:pk>/edit/`, and
      `chores:chore_delete` at `/chores/<int:pk>/delete/` (POST-confirmed
      delete; GET shows a confirmation page) all work and are scoped to the
      user's household; targeting a chore outside the household returns 404.
- [ ] Invalid input (blank name, non-positive cadence or estimate, difficulty
      out of range) re-renders the form with field errors and saves nothing.
- [ ] Every chore view requires login and household membership; an anonymous
      visitor is redirected to login, and a signed-in user with no household is
      redirected to `chores:household_create`.
- [ ] The header nav in `chores/base.html` shows a "Chores" link pointing at
      `chores:chore_list` only for a signed-in user who is in a household
      (`current_household` is set); anonymous visitors and signed-in users with
      no household do not see it. Update the placeholder comment in `base.html`
      accordingly.
- [ ] `Chore` is registered in the admin with `list_display` and a household
      `list_filter`.
- [ ] Tests in `chores/tests/` cover: list scoping, create, edit, delete,
      validation failure, cross-household 404, the no-household redirect, and the
      nav link's visibility condition.
- [ ] `uv run pytest` and `uv run python manage.py check` pass.

## Out of scope

- Generating occurrences from the cadence — task #9.
- People ↔ chore prefer / exclude constraints — task #8.
- A dedicated chore detail page — the edit view is the per-chore page task #8
  builds on; add one only if #8 needs it.
- Re-spacing already-generated occurrences when a chore's cadence changes —
  follow-up: [#27](https://github.com/ckcabang/household-chores/issues/27) (Reconcile occurrences when cadence changes).
- Archive / pause / soft-delete and any richer lifecycle — permanently excluded
  (`_docs/plan.md`).

## Constraints

- Model in `chores/models.py`; the difficulty scale is the single
  `DIFFICULTY_CHOICES` constant described above.
- Class-based views (`ListView` / `CreateView` / `UpdateView` / `DeleteView`)
  in `chores/views.py`, all using the shared `HouseholdScopedMixin`; templates
  live in the `chores` app and extend `chores/base.html`.
- Add the chore routes under `/chores/` in the `chores` URLconf with the URL
  names given above.
- Add the "Chores" link to the nav in `chores/base.html` with the visibility
  condition above.
- No new dependencies.
