# People-to-chore constraints

## Goal

Either member can mark a person as preferred or excluded for a specific
chore, and remove that mark. This task delivers storage plus management
UI only; the assignment algorithm consumes the records later.

## Acceptance criteria

- [ ] `Constraint` model: FK `chore`, FK `membership`, `kind` (`prefer` |
      `exclude` as a choices constant), `created_at`.
- [ ] `UniqueConstraint` on (`chore`, `membership`) — a person has at most one
      mark per chore.
- [ ] `chore` and `membership` must belong to the same household — validated in
      `clean()` and covered by a test.
- [ ] From a chore's detail / edit page a member can add a constraint (choose
      person + kind) and delete an existing one, scoped to the household;
      targeting a chore or membership outside the household returns 404.
- [ ] The chore detail (and/or list) shows the current constraints per chore.
- [ ] Submitting a second constraint for the same (chore, person) is rejected
      with a clear message (chosen behaviour: reject, not silently replace) —
      covered by a test.
- [ ] `Constraint` is registered in the admin.
- [ ] Tests cover: add `prefer`, add `exclude`, uniqueness rejection,
      cross-household rejection, delete.

## Out of scope

- The assignment algorithm reading these constraints — task #14.
- Constraints between the two members (rather than person ↔ chore) — not in the
  MVP (`_docs/plan.md`).

## Constraints

- Model in `chores/models.py`; `kind` is a choices constant shared with
  `chores/fairness/` so the algorithm and the model agree on the values.
- Add / remove use HTMX inline on the chore page, degrading to full-page POSTs.
- CSRF-protected POSTs; no GET mutations.
