# MVP Definition

## Household

- Exactly 2 members.
- Members have equal permissions.
- One household per account.
- Invitation-based joining.

## Chores

- Recurring chores use a flexible cadence, e.g. every 7 days.
- Each occurrence is a distinct completion/history record.
- Minimal states: active → completed, with overdue as a derived state.
- Default: one primary owner.
- Selected chores can support multiple contributors.
- No archive, pause, or complex lifecycle.

## Workload & Fairness

- Each chore has:
  - estimated time
  - difficulty/effort
- Members can submit actual time/effort after completion.
- The system learns from completion history but only proposes estimate changes.
- Fairness is based primarily on equal workload over time.
- Historical contribution uses hidden/automatic decay.
- Preferences/exclusions between people and chores affect assignment.
- Contribution credits from helping another member affect future workload.
- Shared/flexible chores can use those credits.
- Fairness weights start configurable and can evolve from history.
- Member proposals can change estimates or fairness weights.
- Estimate changes can be accepted individually; fairness-weight changes require household approval.

## Assignment

- Automatic assignment.
- Members can define people ↔ chore constraints.
- Assigned member remains the primary owner.
- Another member can claim/help and receive contribution credit.
- The system incorporates that credit into subsequent assignments.
- No trade/negotiation workflow in MVP.
- No automatic reassignment for overdue chores.

## AI Setup

- Guided questions + free-form household description.
- AI generates:
  - chore list
  - cadence
  - time/difficulty estimates
  - initial preferences/constraints where inferable
  - initial assignment plan
  - explanation of its reasoning
- Chores/estimates can activate automatically.
- Initial assignments require member review.

## Dashboard

- Combined view of:
  - current/upcoming chores
  - ownership/status
  - current fairness balance
  - historical contribution
- Completion supports optional actual time/effort feedback.

## Notifications

- None in MVP. Overdue chores are simply flagged.

# Explicitly Out of Scope

Multi-member households, child-specific behavior, multiple households, admin roles, notifications, smart reminders, chore trades, automatic overdue reassignment, archiving, advanced chore lifecycle, external integrations, and sophisticated AI adaptation beyond the defined fairness/estimate learning.
