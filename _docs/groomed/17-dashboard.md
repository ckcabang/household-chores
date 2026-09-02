# Dashboard

## Goal

One read-mostly screen shows current and upcoming occurrences with owner
and status (including derived overdue), the current fairness balance
between the two members, and a short historical-contribution summary.

## Acceptance criteria

- [ ] `GET /dashboard/` requires login and household membership and is linked
      from the nav; a user with no household is redirected to onboarding.
- [ ] It lists occurrences due within a documented window (overdue plus the next
      14 days) showing chore name, due date, owner, and status — with `overdue`
      shown for an `active` occurrence past its due date.
- [ ] It shows the current fairness balance from the task #13 workload function:
      each member's decayed workload and who is ahead, over a documented window.
- [ ] It shows a brief historical-contribution summary (e.g. completions per
      member and contribution credits in the last 30 days).
- [ ] Each listed occurrence has a "mark done" shortcut reusing task #10's
      action; the page has no other mutations.
- [ ] Empty states render cleanly: no chores, no history, and (redirect) no
      household.
- [ ] In a seeded test the numbers on the page match the underlying data.
- [ ] Tests cover: occurrence listing with the overdue flag, balance reflecting
      completions, mark-done from the dashboard, and the empty states.

## Out of scope

- Applying rebalance proposals from this screen — follow-up:
  [#29](https://github.com/ckcabang/household-chores/issues/29) (Apply rebalance proposals) (shared with task #14).
- Charts or trend graphs of contribution over time — follow-up:
  [#31](https://github.com/ckcabang/household-chores/issues/31) (Dashboard contribution charts).
- Any proposal review UI — tasks #15 and #16.

## Constraints

- The view assembles plain data and calls `chores/fairness/`; no fairness math
  in the view or the template.
- Server-rendered; HTMX only for the mark-done action.
- Templates extend `chores/base.html`.
