# Process

- Work is tracked as GitHub issues, taken one at a time. `_docs/tasks.md` is the
  index and the suggested order.
- Every MVP issue has already been groomed against `_docs/task-template.md` - it
  carries a goal, checkable acceptance criteria, out-of-scope items, and
  constraints. The groomed text lives on the issue and in `_docs/groomed/`.
- Each task is sized to a single working session. Read the groomed issue before
  starting, and again before handing it to QA.
- Commit in small steps and push regularly. Reference the issue in the commit
  message (e.g. `refs #7`), but do not use auto-closing keywords - the
  orchestrator closes the issue after QA passes (see Lifecycle).
- Keep the test suite green: CI runs `uv run pytest` on every push and pull request.

Roles

- Engineer - implements one groomed task, follows _docs/team/software-engineer.md
- QA - checks the result against the acceptance criteria, follows _docs/team/qa-engineer.md

(The PM role in _docs/team/pm.md is retained for reference and for grooming any
future follow-up issues, but grooming is not a step in the MVP lifecycle - the
MVP backlog is already groomed.)

Orchestrator

The main session is the orchestrator. It launches the engineer and QA as
subagents. It does not implement or test itself.

Lifecycle

1. Pick the next open issue from the backlog (already groomed)
2. Engineer implements it
3. QA verifies it
4. On FAIL, back to step 2 with the QA comment as input
5. On PASS, close the issue
6. Repeat until the backlog is empty

Rules

- The engineer does not close the issue
- QA does not fix the code, only outputs PASS or FAIL
- The orchestrator closes the issue only after QA outputs PASS
