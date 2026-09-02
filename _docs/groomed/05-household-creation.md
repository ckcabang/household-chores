# Household creation

## Goal

A signed-in user with no household can create one and is recorded as its
first member. A user who already belongs to a household cannot create
another.

## Acceptance criteria

- [ ] `Household` (name, `created_at`) and `Membership` (FK `user`, FK
      `household`, `created_at`) models exist with migrations.
- [ ] A `UniqueConstraint` on `Membership.user` enforces at most one household
      per user at the database level.
- [ ] Creating a third `Membership` for one household raises `ValidationError`;
      the "max 2 members" rule is expressed once and reused by the view and the
      admin.
- [ ] `GET /household/new/` shows a create form (single `name` field) that
      extends `chores/base.html`, to a signed-in user who has no membership.
- [ ] `POST /household/new/` with a blank or whitespace-only `name` re-renders
      the form with an error and creates nothing.
- [ ] `POST /household/new/` with a valid `name` creates the `Household` and the
      creator's `Membership` in one `transaction.atomic` block, then redirects to
      `chores:home`.
- [ ] A signed-in user who already has a membership is redirected to
      `chores:home` with an explanatory message (via `django.contrib.messages`);
      nothing is created, on both `GET` and `POST`.
- [ ] An anonymous visitor to `/household/new/` is redirected to login.
- [ ] A signed-in user with no household sees a "Create a household" link in the
      header nav (and/or on `chores:home`) pointing at `/household/new/`; a user
      who already has a household does not see it.
- [ ] Flash messages are rendered in `chores/base.html` so the redirect message
      above (and messages from later tasks) are visible.
- [ ] `Household` and `Membership` are registered in the admin with useful
      `list_display`.
- [ ] Tests cover: GET renders the form, create success, blank-name rejected,
      already-has-household redirect (GET and POST) with nothing created, third
      membership blocked, anonymous redirect, and the nav link showing only for a
      signed-in user with no household.
- [ ] `uv run pytest` and `uv run python manage.py check` pass.

## Out of scope

- Inviting the second member — task #6.
- Renaming, leaving, or deleting a household, or removing a member — follow-up:
  [#25](https://github.com/ckcabang/household-chores/issues/25) (Leave or dissolve a household).
- Seeding a `FairnessWeights` row when the household is created — task #12 owns
  that step and its test.
- Multi-member households — permanently excluded (`_docs/plan.md`).

## Constraints

- Models in `chores/models.py`.
- The "at most 2 memberships" check lives in one place (a `Membership.clean` /
  `save` guard or a `Household` method) imported by both the view and admin.
- Use `transaction.atomic` for the household + membership creation.
- Add the household routes under `/household/` in the `chores` URLconf.
- View and template live in the `chores` app; the template extends
  `chores/base.html`. Gate access with `LoginRequiredMixin` (or equivalent).
- Use `django.contrib.messages` for the "already has a household" notice; add
  the messages-rendering block to `chores/base.html` as part of this task (it is
  not there yet).
- No new dependencies.
