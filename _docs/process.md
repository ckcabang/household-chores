# Process

- Work is tracked as GitHub issues, taken one at a time. `_docs/tasks.md` is the
  index and the suggested order.
- Before implementation, a task is groomed against `_docs/task-template.md` so the
  issue has a goal, checkable acceptance criteria, out-of-scope items, and constraints.
- Each task is sized to a single working session. Read the groomed issue before
  starting, and again before handing it to QA.
- Commit in small steps and push regularly. Reference the issue in the commit
  message (e.g. `refs #7`), but do not use auto-closing keywords - the
  orchestrator closes the issue after QA passes (see Lifecycle).
- Keep the test suite green: CI runs `uv run pytest` on every push and pull request.

Roles

- PM - grooms a task before anyone implements it, follows _docs/team/pm.md
- Engineer - implements one groomed task, follows _docs/team/software-engineer.md
- QA - checks the result against the acceptance criteria, follows _docs/team/qa-engineer.md

Orchestrator

The main session is the orchestrator. It launches the PM, the engineer
and QA as subagents. It does not groom, implement or test itself.

Lifecycle

1. Pick the next open issue from the backlog
2. PM grooms it
3. Engineer implements it
4. QA verifies it
5. On FAIL, back to step 3 with the QA comment as input
6. On PASS, close the issue
7. Repeat until the backlog is empty

Rules

- Do not skip step 2
- The engineer does not close the issue
- QA does not fix the code, only outputs PASS or FAIL
- The orchestrator closes the issue only after QA outputs PASS
