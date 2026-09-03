# Household Chores

[![CI](https://github.com/ckcabang/household-chores/actions/workflows/ci.yml/badge.svg)](https://github.com/ckcabang/household-chores/actions/workflows/ci.yml)

An app for two-person households to plan, assign, and balance recurring chores fairly.

## What it does

- **Household**: exactly two members with equal permissions, joined by invitation.
- **Chores**: recurring on a flexible cadence (e.g. every 7 days). Each occurrence is its
  own completion record. States are minimal: active → completed, with overdue derived.
- **Workload & fairness**: every chore carries an estimated time and difficulty. Members
  can log actual time/effort after completing a chore, and the system learns from that
  history to *propose* (never silently apply) estimate changes. Fairness targets equal
  workload over time, with automatic decay of older contributions and support for
  contribution credits when one member helps another.
- **Assignment**: automatic, respecting people ↔ chore constraints. The assigned member
  stays the primary owner; the other can claim or help and earn contribution credit that
  feeds into future assignments.
- **AI setup**: guided questions plus a free-form household description generate an initial
  chore list, cadences, estimates, inferred constraints, and a first assignment plan with
  an explanation. Chores and estimates can activate automatically; initial assignments
  require member review.
- **Dashboard**: current and upcoming chores, ownership and status, the current fairness
  balance, and historical contribution in one view.

## Tech stack

- **Django 5.1** (Python 3.12) — web framework, ORM, auth, admin
- **SQLite** for development; Postgres in production
- **HTMX + Alpine.js** for a light frontend (planned)
- **Anthropic API** for AI-assisted setup (planned)

See [`_docs/tech-stack-decision.md`](_docs/tech-stack-decision.md) for why.

## Getting started

Dependencies are managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

`uv sync` creates `.venv/` and installs everything from `uv.lock`. Prefix commands
with `uv run`, or activate the environment (`source .venv/Scripts/activate` on
Windows Git Bash, `source .venv/bin/activate` elsewhere).

### Demo data

`uv run python manage.py seed_demo` builds a complete demo household — two
members, six chores of varying cadence and difficulty, past and upcoming
occurrences, completion history, and a contribution credit — so the dashboard
and fairness screens have something to show. Re-run with `--reset` to rebuild
it; it refuses to run when `DEBUG=False` unless passed `--force`.

| User | Password |
|---|---|
| `demo-alice` | `demo-pass-alice` |
| `demo-bob` | `demo-pass-bob` |

## Configuration

Settings are read from the environment. With no configuration the app runs on
SQLite with `DEBUG` on and an insecure development key — good enough for local work.
For anything else, copy `.env.example` to `.env` (git-ignored) and override:

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | insecure dev key | Set a real one in production. |
| `DEBUG` | `true` | Must be `false` in production. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Comma-separated; required when `DEBUG=false`. |
| `DATABASE_URL` | local SQLite file | e.g. `postgres://user:pass@host:5432/dbname`. The `psycopg` driver is installed. |
| `ANTHROPIC_API_KEY` | unset | Enables AI setup (`/setup/`). Unset: the page shows a "not configured" notice; nothing else is affected. |
| `ANTHROPIC_MODEL` | `claude-opus-5` | Optional override for the model AI setup uses. |

## Running tests

```bash
uv run pytest
```

The suite runs on every push and pull request via GitHub Actions
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Project layout

- `config/` — Django project (settings, root URLconf, WSGI/ASGI)
- `chores/` — main application
  - `chores/templates/chores/` — `base.html` shell and page templates
  - `chores/static/chores/` — stylesheet and vendored HTMX + Alpine
  - `chores/tests/` — the test suite

The front end is server-rendered templates enhanced with
[HTMX](https://htmx.org/) and [Alpine.js](https://alpinejs.dev/), both pinned and
vendored into `chores/static/chores/vendor/` rather than loaded from a CDN.

## Status

Early development. See [`_docs/plan.md`](_docs/plan.md) for the full MVP definition and
what is explicitly out of scope.

## Out of scope (MVP)

Multi-member households, child-specific behavior, multiple households, admin roles,
notifications and smart reminders, chore trades, automatic overdue reassignment,
archiving, advanced chore lifecycle, and external integrations.
