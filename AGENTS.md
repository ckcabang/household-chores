Commands

- `uv sync` - create `.venv/` and install dependencies from `uv.lock`
- `uv run pytest` - run the whole test suite
- `uv run pytest chores/tests/test_smoke.py` - run one test file
- `uv run python manage.py runserver` - run the app locally
- `uv run python manage.py check` - Django system checks
- `uv run python manage.py migrate` - apply migrations

Rules

- Dependencies are declared in `pyproject.toml` and locked in `uv.lock`
  (`uv add <pkg>`, or `uv add --dev <pkg>` for tooling). Both files are
  committed. Do not add a dependency without asking.
- Tests live in `chores/tests/`. Keep the suite green - CI runs `uv run pytest`
  on every push and pull request (`.github/workflows/ci.yml`).
- Fairness logic goes in a framework-agnostic `chores/fairness/` module with
  unit tests, not in views.

Documents

- `_docs/plan.md` - MVP definition and what is out of scope
- `_docs/tech-stack-decision.md` - stack rationale (ADR-001)
- `_docs/tasks.md` - backlog index; each task is a GitHub issue
- `_docs/process.md` - how work is organized
- `_docs/task-template.md` - the shape a groomed issue takes
- `_docs/team/pm.md` - PM role: grooms an issue before implementation
