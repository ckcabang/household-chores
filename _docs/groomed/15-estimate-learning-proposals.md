# Estimate-learning proposals

## Goal

The system compares logged actual times against a chore's current
estimate and, past a configurable threshold, produces an
`EstimateProposal` with a short rationale. Either member can accept one
individually, which updates the chore.

## Acceptance criteria

- [ ] `EstimateProposal` model: FK `chore`, `proposed_minutes` (int), nullable
      `proposed_difficulty`, `rationale` (text), `status`
      (`pending` | `accepted` | `dismissed`), `created_at`, nullable
      `decided_at` and `decided_by` (membership).
- [ ] A pure function in `chores/fairness/` takes a chore's current estimate and
      its completions' `actual_minutes` and returns a proposed estimate +
      rationale when the aggregate (e.g. median of the last N actuals) differs
      from the current estimate by more than a configurable threshold;
      otherwise it returns nothing. N and the threshold are documented
      constants.
- [ ] A command or view runs the function across the household's chores and
      creates `pending` proposals, without creating a second pending proposal
      for a chore that already has one.
- [ ] Pending proposals are listed in the UI showing current vs proposed and
      the rationale.
- [ ] Either member can "accept" (writes `estimated_minutes` / difficulty to the
      chore, marks the proposal `accepted`) or "dismiss" (marks it `dismissed`);
      neither action needs the other member.
- [ ] Accepting or dismissing an already-decided proposal is a no-op; actions
      are household-scoped.
- [ ] `EstimateProposal` is registered in the admin.
- [ ] Tests cover: threshold not met → no proposal, met → proposal, no duplicate
      pending, accept updates the chore, dismiss leaves the chore unchanged.

## Out of scope

- Fairness-weight proposals and their dual approval — task #16.
- Auto-applying estimate changes — the plan requires a member to accept
  (`_docs/plan.md`: "Estimate changes can be accepted individually").
- Notifying members that a proposal exists — no notifications in the MVP.

## Constraints

- The comparison logic is pure and lives in `chores/fairness/`; thresholds and
  the sample window are documented constants there.
- Model and persistence live in the app layer, not the fairness module.
