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
- **HTMX + Alpine.js** for a light frontend, pinned and vendored (no CDN)
- **Anthropic API** for AI-assisted setup
- **Gunicorn + WhiteNoise** in the production image

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

### Periodic commands

The MVP has no scheduler; two management commands are run by hand (or wired to
cron). Both are idempotent — safe to re-run.

| Command | What it does |
|---|---|
| `uv run python manage.py generate_occurrences [--days 30]` | Creates missing chore occurrences across a forward window. |
| `uv run python manage.py propose_estimates` | Turns logged actual times into pending estimate-change proposals. |

Estimate proposals can also be refreshed from the in-app proposals page.

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
| `SECURE_SSL_REDIRECT` / `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` | follow `DEBUG` | On when `DEBUG=false`; override per environment. |
| `SECURE_HSTS_SECONDS` | `0` | Set (e.g. `31536000`) once HTTPS is permanent. `SECURE_HSTS_INCLUDE_SUBDOMAINS` / `SECURE_HSTS_PRELOAD` default true. |
| `SECURE_PROXY_SSL_HEADER` | `false` | Set `true` behind a TLS-terminating proxy that sends `X-Forwarded-Proto`. |

## Running tests

```bash
uv run pytest
```

The suite runs on every push and pull request via GitHub Actions
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Deployment

One settings module driven by environment variables — no `settings/prod.py`.
With `DEBUG=false` the app fails fast at startup unless `ALLOWED_HOSTS` and a
Postgres `DATABASE_URL` are set.

Build and run with the `Dockerfile`:

```bash
docker build -t household-chores .
docker run --rm -p 8000:8000 \
  -e DEBUG=false \
  -e SECRET_KEY=... \
  -e ALLOWED_HOSTS=chores.example.com \
  -e DATABASE_URL=postgres://user:pass@host:5432/chores \
  -e SECURE_PROXY_SSL_HEADER=true \
  household-chores
```

The image runs `collectstatic` at build time; the container command runs
`migrate` and then serves with Gunicorn on port 8000. WhiteNoise serves the
compressed, hashed static files from the same process.

Required in production: `SECRET_KEY`, `DEBUG=false`, `ALLOWED_HOSTS`,
`DATABASE_URL` (Postgres). Optional security switches are in the configuration
table above.

Verify the config (residual warnings such as a weak `SECRET_KEY` are expected
in this smoke form; there should be no errors):

```bash
DEBUG=false SECRET_KEY=$(uv run python -c "from django.core.management.utils import get_random_secret_key as k; print(k())") \
  ALLOWED_HOSTS=example.com DATABASE_URL=postgres://u:p@h/db \
  SECURE_SSL_REDIRECT=true SESSION_COOKIE_SECURE=true CSRF_COOKIE_SECURE=true \
  SECURE_HSTS_SECONDS=31536000 \
  uv run python manage.py check --deploy
```

CI builds the image and runs `check --deploy` against it on every push.

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

MVP complete. All 21 planned tasks (issues #1–#21) are implemented and covered by
the test suite: accounts, household creation and invitations, chore management,
people ↔ chore constraints, occurrences and completion, claiming and helper
credit, configurable fairness weights, decayed workload, automatic assignment
with a rebalance preview, estimate-learning proposals, weight-change proposals
with dual approval, the dashboard, AI setup (plan → review → apply), admin
coverage, demo data, and a production Docker image.

Work beyond the MVP is tracked as follow-up issues #22–#33 (see
[`_docs/groomed/follow-ups.md`](_docs/groomed/follow-ups.md)). See
[`_docs/plan.md`](_docs/plan.md) for the full MVP definition and what is
explicitly out of scope.

## Out of scope (MVP)

Multi-member households, child-specific behavior, multiple households, admin roles,
notifications and smart reminders, chore trades, automatic overdue reassignment,
archiving, advanced chore lifecycle, and external integrations.
