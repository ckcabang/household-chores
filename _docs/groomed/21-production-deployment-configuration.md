# Production deployment configuration

## Goal

The app builds and runs in a production-like environment — Gunicorn,
WhiteNoise static files, a clean `check --deploy`, and documented steps.

## Acceptance criteria

- [ ] A `Dockerfile` (or `Procfile`) builds the app with `uv`, runs
      `migrate`, and starts it under Gunicorn.
- [ ] WhiteNoise is added to `MIDDLEWARE` and `STORAGES` (or
      `STATICFILES_STORAGE`) is set for compressed, hashed static files;
      `collectstatic` runs in the build.
- [ ] With `DEBUG=False` and the documented env vars set,
      `uv run python manage.py check --deploy` reports no errors (remaining
      warnings are triaged in the issue).
- [ ] Production security settings are driven by env vars:
      `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`,
      `CSRF_COOKIE_SECURE`, and `SECURE_PROXY_SSL_HEADER` as appropriate.
- [ ] When `DEBUG=False`, `ALLOWED_HOSTS` and a Postgres `DATABASE_URL` are
      required and a missing one fails fast at startup with a clear message.
- [ ] The README has a "Deployment" section: build, required env vars, run
      command, and how to apply migrations.
- [ ] CI stays green, and a build of the image / Procfile target succeeds
      (locally or in CI).

## Out of scope

- Choosing or provisioning a specific host (Fly, Render, etc.) — decide per
  target when there is one.
- A pipeline that deploys automatically on merge — follow-up:
  [#33](https://github.com/ckcabang/household-chores/issues/33) (Continuous deployment workflow).
- Managed Postgres backups, monitoring, and alerting — a later ops task.

## Constraints

- Keep one settings module; behaviour switches on env vars (consistent with
  task #2). No `settings/prod.py` split unless the issue justifies it.
- No secrets committed; every new env var is added to `.env.example` and the
  README table.
- Add `gunicorn` and `whitenoise` with `uv add` (both pinned) — **ask before
  adding** (`AGENTS.md`).
