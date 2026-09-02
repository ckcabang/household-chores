# Groomed issues

One file per open backlog task (`_docs/tasks.md`), groomed against
[`../task-template.md`](../task-template.md) per the PM role in
[`../team/pm.md`](../team/pm.md): a goal, checkable acceptance criteria,
out-of-scope items with a destination, and constraints.

These files are the **source of truth for the issue body**. The matching
GitHub issue should be updated to match before implementation starts.

## Keeping these in sync with GitHub

These bodies were pushed onto issues #4–#21 with
`scripts/sync_groomed_issues.py`, which also filed the follow-ups
([`follow-ups.md`](follow-ups.md)) as #22–#33 and resolved the references.
To re-apply after editing a groomed file:

```bash
uv run python scripts/sync_groomed_issues.py --dry-run   # preview
uv run python scripts/sync_groomed_issues.py             # apply
```

It authenticates via `git credential fill` for github.com (or `GITHUB_TOKEN`)
and never prints the token. Follow-ups already present by title are reused,
not duplicated.

## Status of the backlog

| # | Task | Groomed |
|---|------|---------|
| 1–3 | skeleton, settings, front-end shell | closed, not re-groomed |
| 4 | [User accounts](04-user-accounts.md) | ✅ |
| 5 | [Household creation](05-household-creation.md) | ✅ |
| 6 | [Invitation flow](06-invitation-flow.md) | ✅ |
| 7 | [Chore management](07-chore-management.md) | ✅ |
| 8 | [People-to-chore constraints](08-people-to-chore-constraints.md) | ✅ |
| 9 | [Chore occurrences](09-chore-occurrences.md) | ✅ |
| 10 | [Completing an occurrence](10-completing-an-occurrence.md) | ✅ |
| 11 | [Claiming and helper credit](11-claiming-and-helper-credit.md) | ✅ |
| 12 | [Fairness weights](12-fairness-weights.md) | ✅ |
| 13 | [Workload calculation with decay](13-workload-calculation-with-decay.md) | ✅ |
| 14 | [Automatic assignment](14-automatic-assignment.md) | ✅ |
| 15 | [Estimate-learning proposals](15-estimate-learning-proposals.md) | ✅ |
| 16 | [Weight-change proposals with approval](16-weight-change-proposals-with-approval.md) | ✅ |
| 17 | [Dashboard](17-dashboard.md) | ✅ |
| 18 | [AI setup — plan generation](18-ai-setup-plan-generation.md) | ✅ |
| 19 | [AI setup — review and apply](19-ai-setup-review-and-apply.md) | ✅ |
| 20 | [Admin coverage and demo data](20-admin-coverage-and-demo-data.md) | ✅ |
| 21 | [Production deployment configuration](21-production-deployment-configuration.md) | ✅ |
