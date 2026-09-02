# People-to-chore constraints

## Goal

Either member can mark a person as preferred or excluded for a specific
chore, and remove that mark, from the chore's edit page. This task delivers
storage plus management UI only; the assignment algorithm (task #14) consumes
the records later.

## Acceptance criteria

- [ ] `Constraint` model in `chores/models.py`, with a migration: FK `chore`
      (`on_delete=CASCADE`), FK `membership` (`on_delete=CASCADE`), `kind`
      (`choices=CONSTRAINT_KIND_CHOICES`), `created_at`
      (`auto_now_add=True`).
- [ ] The kind scale is defined once as a module-level constant
      `CONSTRAINT_KIND_CHOICES` in `chores/models.py` — a plain list of
      `(value, label)` pairs, e.g.
      `[("prefer", "Preferred"), ("exclude", "Excluded")]`, **not**
      `models.TextChoices` — mirroring the existing `DIFFICULTY_CHOICES`
      decision, so the framework-agnostic `chores/fairness/` package (created
      by task #13) and the assignment algorithm (#14) can import the values
      without pulling in Django's model layer.
- [ ] `UniqueConstraint` on (`chore`, `membership`) — a person has at most one
      mark per chore.
- [ ] `chore` and `membership` must belong to the same household — validated in
      `Constraint.clean()` and covered by a test.
- [ ] The chore edit page (`chores:chore_edit` at `/chores/<int:pk>/edit/` —
      there is no separate chore detail view; see task #7 out of scope) gains a
      "Constraints" section that lists this chore's current constraints (person +
      kind) each with a delete control, and a small form to add one (choose
      person + kind). The person dropdown lists only the current household's
      memberships.
- [ ] `chores:chore_list` shows each chore's current constraints (a per-row
      summary — e.g. "Alex: preferred, Sam: excluded", or "None").
- [ ] Adding a constraint: `POST` to `chores:constraint_add` at
      `/chores/<int:chore_pk>/constraints/add/` creates the `Constraint` scoped
      to the current household and redirects back to the chore edit page.
- [ ] Deleting a constraint: `POST` to `chores:constraint_delete` at
      `/chores/<int:chore_pk>/constraints/<int:pk>/delete/` deletes it and
      redirects back to the chore edit page.
- [ ] Both views use `HouseholdScopedMixin`: an anonymous visitor is redirected
      to login; a signed-in user with no household is redirected to
      `chores:household_create`. A `chore_pk`, constraint `pk`, or submitted
      `membership` that belongs to another household returns 404.
- [ ] Both mutations are POST-only and CSRF-protected; a GET to either URL is
      rejected (405 or redirect) and mutates nothing.
- [ ] Submitting a second constraint for the same (chore, person) is rejected
      (chosen behaviour: reject, not silently replace) and the chore edit page
      re-renders with a clear message; nothing is created — covered by a test.
- [ ] `Constraint` is registered in the admin with `list_display`
      (chore, membership, kind, created_at) and a `list_filter` on `kind`.
- [ ] Tests in `chores/tests/` cover: add `prefer`, add `exclude`, uniqueness
      rejection, cross-household rejection (chore and membership), delete, the
      GET-rejected-on-mutation-URLs case, and the constraints showing on the
      chore edit page and list.
- [ ] `uv run pytest` and `uv run python manage.py check` pass.

## Out of scope

- The assignment algorithm reading these constraints — task #14.
- Creating the `chores/fairness/` package — task #13; this task only places the
  shared `CONSTRAINT_KIND_CHOICES` constant where #13 and #14 can import it.
- A dedicated chore detail view — the edit page is the per-chore page (task #7
  out of scope); do not add one.
- Constraints between the two members (rather than person ↔ chore) — not in the
  MVP (`_docs/plan.md`).

## Constraints

- Model, constant, and `clean()` in `chores/models.py`. `kind` uses
  `CONSTRAINT_KIND_CHOICES` as described above.
- Views in `chores/views.py` using the existing `HouseholdScopedMixin`; routes
  in the `chores` URLconf with the URL names given above; templates in the
  `chores` app extending `chores/base.html`.
- CSRF-protected POSTs; no GET mutations.
- `chores/base.html` already loads HTMX 2.0.4 and sets the `X-CSRFToken` header
  on `<body>`. The add / remove controls MAY use HTMX to swap just the
  constraints section, but the plain full-page POST path is the requirement and
  must work on its own; HTMX is an optional progressive enhancement.
- No new dependencies.
