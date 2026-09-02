# Tech Stack Decision

**Status:** Accepted · **Date:** 2026-09-02 · **Decision owner:** Clarence Cabang

## Decision

Build the MVP with **Django 5.1 (Python 3.12)** and server-rendered templates,
progressively enhanced with **HTMX + Alpine.js**. SQLite in development, Postgres in
production. The **Anthropic API** powers the AI-assisted setup flow.

## Context

The MVP (see [`plan.md`](plan.md)) is a two-person household chore planner. The technical
shape that drives the choice:

- **Tiny scale.** Two members per household, one household per account. No performance or
  concurrency pressure anywhere.
- **Structured relational data.** Households, members, chores, occurrences, completions,
  contribution credits, people↔chore constraints, estimate/weight proposals. A normalized
  schema, not a document store.
- **A fairness engine.** Decay of historical contribution, contribution credits,
  constraint-respecting automatic assignment, "learn from history but only *propose*
  changes." Pure, deterministic logic that must be its own well-tested module.
- **One LLM interaction.** AI setup turns guided answers plus free-form text into
  structured output (chore list, cadences, estimates, constraints, assignment plan,
  reasoning). Needs schema-validated structured output; can be a slow request.
- **A modest dashboard.** Mostly read views plus a few mutations. Not a heavily
  interactive SPA.
- **No notifications, no required background jobs.** Overdue is derived; decay is computed
  on read. The whole MVP can ship with zero workers.

## Options considered

| Option | Summary | Why not (for the MVP) |
| --- | --- | --- |
| **A. Next.js + Postgres + Drizzle** (TypeScript) | RSC + Server Actions, largest ecosystem, best AI-assist support | App Router complexity is overkill for a 6-table app; serverless timeouts complicate the slow AI call; you assemble auth and admin yourself |
| **B. Remix / React Router 7 + Postgres + Drizzle** (TypeScript) | loader/action maps 1:1 to CRUD; plain Node server, no timeout worries | Smaller ecosystem; still hand-wire auth; no built-in data browser for debugging the fairness engine |
| **C. Django + HTMX/Alpine** (Python) — **chosen** | Batteries included; admin panel; Python suits the stats-flavored learning logic | HTMX has a ceiling if the dashboard later needs to be genuinely app-like |
| **D. Rails 8 + Hotwire** (Ruby) | Same "conventions decide the boring stuff" pitch; strong built-in jobs | Ruby is the least natural of these for stats/learning logic; smaller talent pool; weaker structured-LLM tooling |
| **E. SvelteKit + SQLite** (TypeScript) | Least boilerplate, cheapest to run | Smallest ecosystem and community; fewer worked examples for auth and LLM structured output |

## Rationale

1. **The admin panel is a real advantage here.** A two-person app where we constantly
   inspect completion history, credits, and why the assigner chose X — Django's admin is a
   full data browser and editor on day one, for free.
2. **Python fits the core problem.** The fairness learning ("learn from history, propose
   estimate changes") is stats-flavored work. Python keeps it in one toolchain now and
   leaves room to reach for numpy/pandas or a light regression later.
3. **Fastest path to a working data-backed app.** ORM, migrations, auth, sessions,
   CSRF, and forms are built in. We spend our time on the fairness engine, not plumbing.
4. **The frontend is light enough.** The dashboard is read-heavy with a handful of
   mutations; HTMX + Alpine cover it without an SPA build pipeline.
5. **Structured LLM output is well supported** in the Anthropic Python SDK — treat the
   model's output as a draft that a schema validates, matching the plan's "assignments
   require review."

## Consequences

- **If the dashboard later needs to be genuinely app-like** (drag-to-reassign, live
  rebalancing previews), HTMX will strain and we add a JS island or a partial SPA. This is
  an accepted, deferred risk.
- **Two languages if we ever add a rich React frontend.** Acceptable; not on the MVP path.
- The **fairness engine is framework-agnostic** — a pure-Python package with exhaustive
  unit tests, not logic living in views. This keeps a future migration cheap.

## Cross-cutting choices (independent of framework)

- **Database:** SQLite for local development, Postgres in production.
- **Fairness engine** lives in its own module (`chores/fairness/` or a sibling package),
  pure functions, exhaustively unit-tested: decay, credits, constraint solving, proposal
  generation.
- **AI setup:** structured output via JSON schema / tool use; the model's output is a
  draft the schema validates before anything activates.
- **Invitations:** signed invite links; no email infrastructure for the MVP.
- **Derived state:** compute overdue and decayed contribution on read; do not store or
  schedule them until there is a concrete reason.

## Project layout

- `config/` — Django project: settings, root URLconf, WSGI/ASGI entry points.
- `chores/` — the main application: models, views, templates, and the fairness engine.
