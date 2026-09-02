Commands

- `python -m venv .venv` then `source .venv/Scripts/activate` (Windows, Git Bash)
  or `source .venv/bin/activate` (macOS/Linux) - create and enter the virtualenv
- `pip install -r requirements.txt` - install dependencies
- `pytest` - run the whole test suite
- `pytest chores/tests/test_smoke.py` - run one test file
- `python manage.py runserver` - run the app locally
- `python manage.py check` - Django system checks
- `python manage.py migrate` - apply migrations

Rules

- Dependencies are pinned in `requirements.txt`. After `pip install`, run
  `pip freeze > requirements.txt`. Do not add a dependency without asking.
- Tests live in `chores/tests/`. Keep the suite green - CI runs `pytest` on
  every push and pull request (`.github/workflows/ci.yml`).
- Fairness logic goes in a framework-agnostic `chores/fairness/` module with
  unit tests, not in views.

Documents

- `_docs/plan.md` - MVP definition and what is out of scope
- `_docs/tech-stack-decision.md` - stack rationale (ADR-001)
- `_docs/tasks.md` - backlog index; each task is a GitHub issue
- `_docs/process.md` - how work is organized
