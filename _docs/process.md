# Process

- Work is tracked as GitHub issues, taken one at a time. `_docs/tasks.md` is the
  index and the suggested order.
- Each task is sized to a single working session. Read the issue's goal and
  description before starting, and again before closing it.
- Commit in small steps and push regularly. Reference the issue in the commit
  message (e.g. `closes #7`) so it closes when the change lands on `main`.
- Keep the test suite green: CI runs `pytest` on every push and pull request.

Roles

- PM - grooms a task before anyone implements it, follows _docs/team/pm.md