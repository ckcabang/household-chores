# Weight-change proposals with approval

## Goal

A `WeightProposal` holds proposed fairness-weight values and each
member's approval. The values are written to the household only when both
members approve.

## Acceptance criteria

- [ ] `WeightProposal` model: FK `household`, the proposed values (mirroring the
      `FairnessWeights` fields), FK `created_by` (membership), per-member
      approval state (two booleans or an approvals set), `status`
      (`open` | `applied` | `rejected`), `created_at` / `resolved_at`.
- [ ] `GET`/`POST /household/fairness/proposals/new/` lets a member propose new
      values from a form pre-filled with the current weights.
- [ ] The proposal detail page shows proposed vs current values and each
      member's approval state.
- [ ] The creator is recorded as approving on creation; the other member can
      approve or reject.
- [ ] When both members approve, the values are written to the household's
      `FairnessWeights` in one `transaction.atomic` block, the proposal becomes
      `applied`, and the new values show on the fairness screen.
- [ ] When either member rejects, the proposal becomes `rejected` and the
      weights are unchanged.
- [ ] Only one `open` proposal per household at a time — creating a second while
      one is open is blocked with a clear message (chosen behaviour; tested).
- [ ] Approving or rejecting an already-`applied`/`rejected` proposal is a
      no-op.
- [ ] `WeightProposal` is registered in the admin.
- [ ] Tests cover: create (creator auto-approves), second approval applies the
      values, a rejection leaves weights untouched, the single-open-proposal
      rule, no-op on a closed proposal.

## Out of scope

- Direct weight editing without approval — task #12. This task disables or gates
  that form while proposals are the path; note the decision in the issue.
- An audit log / history of past weight changes — follow-up:
  [#30](https://github.com/ckcabang/household-chores/issues/30) (Fairness weight change history).
- Notifying the other member of a pending proposal — no notifications in the
  MVP.

## Constraints

- Reuse the `FairnessWeights` field definitions via a shared form or mixin so
  the two models cannot drift apart.
- The apply step is atomic.
