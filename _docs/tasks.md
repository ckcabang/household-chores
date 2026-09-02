# Backlog

The tasks below now live as [GitHub issues](https://github.com/ckcabang/household-chores/issues).
This file is just the index and the suggested order; the numbering is a recommended
sequence, not a hard dependency chain.

Before implementation, each issue is groomed against [`task-template.md`](task-template.md)
into a goal, checkable acceptance criteria, out-of-scope items, and constraints. The full
groom → implement → verify lifecycle and the roles that run it are in
[`process.md`](process.md).

Tasks 4–21 have been groomed; the groomed text lives in [`groomed/`](groomed/) and on the
issues themselves. Out-of-scope items are tracked as follow-up issues #22–#33, indexed in
[`groomed/follow-ups.md`](groomed/follow-ups.md).

Context for every task: the MVP is defined in [`plan.md`](plan.md); the stack and structure
are set by [`tech-stack-decision.md`](tech-stack-decision.md) — Django 5.1, server-rendered
templates with HTMX + Alpine, fairness logic in a framework-agnostic `chores/fairness/`
module. Each task is scoped to a single working session.

| # | Task | Issue |
|---|------|-------|
| 1 | Project skeleton with a passing test | [#1](https://github.com/ckcabang/household-chores/issues/1) |
| 2 | Environment-based settings and Postgres support | [#2](https://github.com/ckcabang/household-chores/issues/2) |
| 3 | Base layout and front-end shell | [#3](https://github.com/ckcabang/household-chores/issues/3) |
| 4 | User accounts | [#4](https://github.com/ckcabang/household-chores/issues/4) |
| 5 | Household creation | [#5](https://github.com/ckcabang/household-chores/issues/5) |
| 6 | Invitation flow | [#6](https://github.com/ckcabang/household-chores/issues/6) |
| 7 | Chore management | [#7](https://github.com/ckcabang/household-chores/issues/7) |
| 8 | People-to-chore constraints | [#8](https://github.com/ckcabang/household-chores/issues/8) |
| 9 | Chore occurrences | [#9](https://github.com/ckcabang/household-chores/issues/9) |
| 10 | Completing an occurrence | [#10](https://github.com/ckcabang/household-chores/issues/10) |
| 11 | Claiming and helper credit | [#11](https://github.com/ckcabang/household-chores/issues/11) |
| 12 | Fairness weights | [#12](https://github.com/ckcabang/household-chores/issues/12) |
| 13 | Workload calculation with decay | [#13](https://github.com/ckcabang/household-chores/issues/13) |
| 14 | Automatic assignment | [#14](https://github.com/ckcabang/household-chores/issues/14) |
| 15 | Estimate-learning proposals | [#15](https://github.com/ckcabang/household-chores/issues/15) |
| 16 | Weight-change proposals with approval | [#16](https://github.com/ckcabang/household-chores/issues/16) |
| 17 | Dashboard | [#17](https://github.com/ckcabang/household-chores/issues/17) |
| 18 | AI setup — plan generation | [#18](https://github.com/ckcabang/household-chores/issues/18) |
| 19 | AI setup — review and apply | [#19](https://github.com/ckcabang/household-chores/issues/19) |
| 20 | Admin coverage and demo data | [#20](https://github.com/ckcabang/household-chores/issues/20) |
| 21 | Production deployment configuration | [#21](https://github.com/ckcabang/household-chores/issues/21) |

## Follow-ups (not on the MVP path)

Filed while grooming; each needs its own grooming pass before implementation.

| # | Task | Issue |
|---|------|-------|
| 22 | Password reset flow | [#22](https://github.com/ckcabang/household-chores/issues/22) |
| 23 | Collect and verify email on signup | [#23](https://github.com/ckcabang/household-chores/issues/23) |
| 24 | Throttle failed login attempts | [#24](https://github.com/ckcabang/household-chores/issues/24) |
| 25 | Leave or dissolve a household | [#25](https://github.com/ckcabang/household-chores/issues/25) |
| 26 | Revoke and regenerate invitations | [#26](https://github.com/ckcabang/household-chores/issues/26) |
| 27 | Reconcile occurrences when cadence changes | [#27](https://github.com/ckcabang/household-chores/issues/27) |
| 28 | Undo a completion | [#28](https://github.com/ckcabang/household-chores/issues/28) |
| 29 | Apply rebalance proposals | [#29](https://github.com/ckcabang/household-chores/issues/29) |
| 30 | Fairness weight change history | [#30](https://github.com/ckcabang/household-chores/issues/30) |
| 31 | Dashboard contribution charts | [#31](https://github.com/ckcabang/household-chores/issues/31) |
| 32 | Regenerate AI setup draft | [#32](https://github.com/ckcabang/household-chores/issues/32) |
| 33 | Continuous deployment workflow | [#33](https://github.com/ckcabang/household-chores/issues/33) |
