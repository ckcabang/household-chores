# Automatic assignment

## Goal

`chores/fairness/` exposes a pure function that proposes a primary owner
for each upcoming chore, moving the household toward equal workload while
never assigning an excluded member. A "rebalance" view previews the
proposal without applying it.

## Acceptance criteria

- [ ] The assignment function is pure (no Django imports) and takes: the chores
      to assign (id, workload cost, current owner id), the current per-member
      workload (output of task #13), and the constraints (member ↔ chore
      `prefer` / `exclude`).
- [ ] It never proposes a member marked `exclude` for that chore. If both
      members are excluded, the chore is returned as `unassignable` rather than
      forced onto someone.
- [ ] `prefer` biases but does not override balance: a tie between members is
      broken toward a preferred member, then deterministically (e.g. lower
      member id).
- [ ] Assignment is greedy over chores in decreasing cost order — each chore
      goes to the eligible member with the lower projected workload — and the
      result is deterministic for a given input.
- [ ] The return value gives, per chore, the proposed owner (or `unassignable`)
      and the resulting projected workload for each member.
- [ ] Unit tests cover: two chores + one idle member (both go to the idle
      member), an exclusion forcing the other member, both members excluded →
      `unassignable`, a preference breaking a tie, empty input.
- [ ] `GET /household/rebalance/` shows, per upcoming chore, the current owner
      vs the proposed owner, plus the projected balance before and after. It
      writes nothing.

## Out of scope

- Writing proposed owners back to chores or occurrences — follow-up:
  [#29](https://github.com/ckcabang/household-chores/issues/29) (Apply rebalance proposals).
- Automatic reassignment of overdue chores — permanently excluded
  (`_docs/plan.md`).
- Any trade / negotiation workflow between members — permanently excluded
  (`_docs/plan.md`).

## Constraints

- Pure module in `chores/fairness/`; the view adapts ORM data in and renders
  the preview out.
- Reuse the task #13 workload function — do not reimplement decay or the
  workload formula.
- Deterministic: no randomness, no wall-clock reads inside the function.
