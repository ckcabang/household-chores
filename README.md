# Household Chores

An app for two-person households to plan, assign, and balance recurring chores fairly.

## What it does

- **Household**: exactly two members with equal permissions, joined by invitation.
- **Chores**: recurring on a flexible cadence (e.g. every 7 days). Each occurrence is its
  own completion record. States are minimal: active → completed, with overdue derived.
- **Workload & fairness**: every chore carries an estimated time and difficulty. Members
  can log actual time/effort after completing a chore, and the system learns from that
  history to *propose* (never silently apply) estimate changes. Fairness targets equal
  workload over time, with automatic decay of older contributions and support for
  contribution credits when one member helps another.
- **Assignment**: automatic, respecting people ↔ chore constraints. The assigned member
  stays the primary owner; the other can claim or help and earn contribution credit that
  feeds into future assignments.
- **AI setup**: guided questions plus a free-form household description generate an initial
  chore list, cadences, estimates, inferred constraints, and a first assignment plan with
  an explanation. Chores and estimates can activate automatically; initial assignments
  require member review.
- **Dashboard**: current and upcoming chores, ownership and status, the current fairness
  balance, and historical contribution in one view.

## Status

Early development. See [`_docs/plan.md`](_docs/plan.md) for the full MVP definition and
what is explicitly out of scope.

## Out of scope (MVP)

Multi-member households, child-specific behavior, multiple households, admin roles,
notifications and smart reminders, chore trades, automatic overdue reassignment,
archiving, advanced chore lifecycle, and external integrations.
