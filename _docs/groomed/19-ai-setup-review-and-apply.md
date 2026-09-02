# AI setup — review and apply

## Goal

Members review a validated draft plan, edit or drop items, and confirm.
On confirm the real `Chore` and `Constraint` records are created; chores
and estimates activate immediately, while assignments are flagged as
needing review.

## Acceptance criteria

- [ ] `GET /setup/review/` renders the latest `draft` `AISetupDraft`: chores
      with editable `name` / `cadence_days` / `estimated_minutes` /
      `difficulty`, constraints (removable / toggleable), proposed assignments,
      and the AI's `reasoning` text.
- [ ] A member can edit any field and remove any chore or constraint before
      confirming; edits are saved back to the draft and survive a page reload.
- [ ] "Confirm" creates `Chore` rows (active) and `Constraint` rows from the
      edited plan in one `transaction.atomic` block, marks the draft `applied`,
      and redirects to the dashboard.
- [ ] Proposed assignments are recorded as needing review (e.g. `primary_owner`
      set plus an `assignment_needs_review` flag, or rebalance-style proposals)
      — never silently treated as final.
- [ ] Confirming a draft that is already `applied` does not double-create; it
      redirects with a message.
- [ ] If no draft exists, `/setup/review/` redirects to `/setup/`.
- [ ] The page is household-scoped; a non-member gets 403.
- [ ] Tests cover: draft renders, an edit persists, confirm creates chores and
      constraints, assignments are flagged, double-confirm is guarded, no-draft
      redirect.

## Out of scope

- Generating the plan — task #18.
- Resolving the flagged assignments — task #14's rebalance view / the dashboard.
- Regenerating the plan from new answers — follow-up:
  [#32](https://github.com/ckcabang/household-chores/issues/32) (Regenerate AI setup draft).

## Constraints

- Reuse the `Chore` and `Constraint` model validation from tasks #7 and #8 —
  the applied plan must pass the same checks as manually entered data.
- Record creation is atomic: a partial apply must not leave half a plan.
