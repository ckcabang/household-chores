# Follow-up issues

Work moved out of scope while grooming #4–#21, now filed as GitHub issues
#22–#33 and linked from each parent's "Out of scope" section.

None of these are on the MVP critical path; they are captured so nothing is
silently dropped. Each still needs grooming against `_docs/task-template.md`
before implementation.

| Issue | Title | Raised by | One-line goal |
|---|---|---|---|
| [#22](https://github.com/ckcabang/household-chores/issues/22) | Password reset flow | #4 | A user who forgot their password can reset it. Blocked on email infrastructure, which the MVP omits — revisit once email exists. |
| [#23](https://github.com/ckcabang/household-chores/issues/23) | Collect and verify email on signup | #4 | Signup captures an email address and confirms it before it is trusted. |
| [#24](https://github.com/ckcabang/household-chores/issues/24) | Throttle failed login attempts | #4 | Repeated failed logins for one account or IP are rate-limited or briefly locked out. |
| [#25](https://github.com/ckcabang/household-chores/issues/25) | Leave or dissolve a household | #5 | A member can leave a household, and a household with no members is cleaned up; renaming a household is included. |
| [#26](https://github.com/ckcabang/household-chores/issues/26) | Revoke and regenerate invitations | #6 | The inviting member can invalidate an outstanding invite link and issue a fresh one. |
| [#27](https://github.com/ckcabang/household-chores/issues/27) | Reconcile occurrences when cadence changes | #7, #9 | Editing a chore's `cadence_days` re-spaces its future (not past) occurrences instead of leaving stale ones. |
| [#28](https://github.com/ckcabang/household-chores/issues/28) | Undo a completion | #10 | A member can reverse a mistaken completion, restoring the occurrence to `active` and removing the `Completion` (and any credit). |
| [#29](https://github.com/ckcabang/household-chores/issues/29) | Apply rebalance proposals | #14, #17 | The proposed owners from the rebalance preview can be written to the chores in one confirmed action. |
| [#30](https://github.com/ckcabang/household-chores/issues/30) | Fairness weight change history | #16 | Past `FairnessWeights` changes are recorded with who/when/what so the household can see how weights evolved. |
| [#31](https://github.com/ckcabang/household-chores/issues/31) | Dashboard contribution charts | #17 | The dashboard gains a visual trend of contribution / balance over time. |
| [#32](https://github.com/ckcabang/household-chores/issues/32) | Regenerate AI setup draft | #19 | From the review screen, a member can discard the draft and generate a new one with revised answers. |
| [#33](https://github.com/ckcabang/household-chores/issues/33) | Continuous deployment workflow | #21 | Merges to `main` build and deploy automatically to the chosen host. |

## Suggested body for each follow-up

```
**Goal:** <the one-line goal above>

Raised while grooming <parent issue link(s)> — moved out of scope so the
parent task stays sized to one session. Not on the MVP critical path.

Groom against `_docs/task-template.md` before implementing.
```
