# Claiming and helper credit

## Goal

When someone other than the owner does a chore — by claiming it or by
completing it directly — a `ContributionCredit` row records that the
helper did work owned by the other member. This task is accurate capture
only; no fairness math.

## Acceptance criteria

- [ ] `ContributionCredit` model: FK `occurrence`, FK `helper` → `Membership`,
      FK `owner` → `Membership`, `workload_value` (Decimal/float), `created_at`.
- [ ] A "claim" action lets a member take an `active` occurrence they do not
      own; the chore's `primary_owner` is unchanged.
- [ ] Completing an occurrence as a non-owner (the task #10 path, or after
      claiming) creates exactly one `ContributionCredit`; the owner completing
      their own occurrence creates none.
- [ ] `workload_value` is computed at completion time from the chore's estimate
      and the household's fairness weights, via a shared helper in
      `chores/fairness/` (documented formula).
- [ ] `helper` and `owner` are always the two distinct memberships of the
      household — a credit is never self-owned (validated, tested).
- [ ] One completion yields at most one credit — re-running completion does not
      add another.
- [ ] `ContributionCredit` is registered in the admin.
- [ ] Tests cover: non-owner completion → credit, owner completion → no credit,
      claim then complete → credit, `workload_value` captured correctly, no
      duplicate on repeat.

## Out of scope

- Spending credits on shared / flexible chores and feeding them into
  assignment — consumed by tasks #13 and #14.
- The fairness math itself (decay, balance) — task #13.

## Constraints

- Model in `chores/models.py`.
- The `workload_value` derivation is a single function in `chores/fairness/`,
  reused here and by the workload calculation, so capture and later math cannot
  drift.
- Claim and complete actions are CSRF-protected POSTs, household-scoped.
