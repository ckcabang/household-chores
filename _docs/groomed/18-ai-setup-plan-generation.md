# AI setup — plan generation

## Goal

A questionnaire plus a free-text household description is sent to the
Anthropic API and a schema-validated draft plan is stored. Nothing is
applied to the household in this task.

## Acceptance criteria

- [ ] `GET`/`POST /setup/` collects guided answers (household size is fixed at
      2 — e.g. home type, number of rooms, pets, standout preferences) plus a
      free-form description.
- [ ] On submit the app calls the Anthropic API requesting structured output
      matching a defined JSON schema: chores (`name`, `cadence_days`,
      `estimated_minutes`, `difficulty`), inferred constraints (person, chore,
      `prefer`/`exclude`), an initial assignment (chore → member), and a
      `reasoning` summary string.
- [ ] The response is validated against the schema; on validation failure the
      user sees a retry message and no draft is saved.
- [ ] A valid response is stored as an `AISetupDraft` (FK `household`, raw JSON,
      parsed fields, `created_at`, `status="draft"`).
- [ ] The API key is read from `ANTHROPIC_API_KEY` in the environment; a missing
      key produces a clear configuration error, not a traceback.
- [ ] The API call has a timeout, and its failure (network error, 4xx, 5xx) is
      shown as a friendly message.
- [ ] No `Chore`, `Constraint`, or assignment records are created in this task.
- [ ] Tests use a stubbed API client (no network in CI): valid response → draft
      saved; schema-invalid response → no draft + error; API error → friendly
      message.

## Out of scope

- Reviewing, editing, or applying the draft — task #19.
- Streaming or progress UI for the request — not needed for the MVP.
- Any household size other than 2 — permanently fixed (`_docs/plan.md`).

## Constraints

- Add the `anthropic` package with `uv add` (pinned) — **ask before adding**
  (`AGENTS.md`).
- Anthropic-specific code is isolated in one module (e.g. `chores/ai/setup.py`)
  behind a function that returns the parsed plan or raises. Check the
  `claude-api` skill for the current model id and structured-output usage.
- The client is injectable so tests run without a real key; CI must not need
  one.
- Document `ANTHROPIC_API_KEY` in `.env.example` and the README.
