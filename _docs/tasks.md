# Backlog

The tasks below now live as [GitHub issues](https://github.com/ckcabang/household-chores/issues).
This file is just the index and the suggested order; the numbering is a recommended
sequence, not a hard dependency chain.

Before implementation, each issue is groomed against [`task-template.md`](task-template.md)
into a goal, checkable acceptance criteria, out-of-scope items, and constraints — see
[`process.md`](process.md). The issues as first filed only carry a goal and a short
description.

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
