# Completing an occurrence

## Goal

A member can mark an active occurrence done and optionally record actual
time and effort. A `Completion` row captures who did it and the logged
values — the raw data later consumed by fairness and estimate learning.

## Acceptance criteria

- [ ] `Completion` model: `OneToOneField` to `ChoreOccurrence`, FK
      `completed_by` → `Membership`, nullable `actual_minutes` (positive int),
      nullable `actual_effort` (small int, same scale as `Chore.difficulty`),
      `created_at`.
- [ ] A "mark done" POST on an `active` occurrence sets `status=completed` and
      `completed_at=now`, and creates the `Completion`; optional actual minutes
      and effort come from the same form.
- [ ] Posting "mark done" on an already-completed occurrence is a no-op with a
      message — no second `Completion` is created.
- [ ] Only members of the occurrence's household can complete it; anyone else
      gets a 404.
- [ ] Actual values are optional, but when present must be positive and
      in range — otherwise the form re-renders with errors and nothing changes.
- [ ] `Completion` is registered in the admin.
- [ ] Tests cover: complete without feedback, complete with feedback,
      double-complete guarded, cross-household 404, invalid actual values.

## Out of scope

- A non-owner completion creating contribution credit — task #11.
- Undoing or reopening a completion — follow-up: [#28](https://github.com/ckcabang/household-chores/issues/28) (Undo a completion).
- Any fairness or estimate math over completions — tasks #13 and #15.

## Constraints

- Model in `chores/models.py`; the effort scale is the shared choices constant
  from task #7, not a new one.
- The "mark done" control lives on the occurrence list / dashboard as a
  CSRF-protected POST, HTMX-enhanced for inline update.
- Flipping the occurrence and writing the `Completion` happen in one
  `transaction.atomic` block.
