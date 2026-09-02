# Fairness weights

## Goal

Every household has exactly one `FairnessWeights` row, created with
documented defaults when the household is created, and either member can
edit its values directly.

## Acceptance criteria

- [ ] `FairnessWeights` model: `OneToOneField` to `Household`; fields for the
      time-vs-difficulty weighting (e.g. `time_weight` and `difficulty_weight`
      floats, or a single 0–1 `time_share`), `decay_half_life_days` (positive
      int), and any other factor the workload function needs — each with a
      default defined once and documented alongside `chores/fairness/`.
- [ ] Creating a `Household` (task #5's view **and** the admin) also creates its
      `FairnessWeights` with defaults; a data migration or `get_or_create`
      backfills any household lacking one.
- [ ] `GET /household/fairness/` shows the current values in an editable form to
      a member; a non-member gets 403 or a redirect.
- [ ] Posting valid values updates the row and re-renders with a success
      message.
- [ ] Posting invalid values (non-positive half-life, a weight outside its
      allowed range) is rejected with field errors and changes nothing.
- [ ] Validation is enforced on the model (`validators=` / `clean`) as well as
      the form.
- [ ] `FairnessWeights` is registered in the admin.
- [ ] Tests cover: default row created with the household, backfill for an
      existing household, edit success, validation rejection, non-member denied.

## Out of scope

- Requiring both members to approve a weight change before it takes effect —
  task #16 layers that on top (and gates or removes this direct-edit form).
- Weights evolving automatically from history — not in the MVP beyond estimate
  learning (`_docs/plan.md`).
- The workload math that reads these values — task #13.

## Constraints

- Model in `chores/models.py`; the numeric defaults and their meaning are
  documented in `chores/fairness/` so the pure functions and the model agree.
- No fairness computation in the view — this task only stores and edits values.
