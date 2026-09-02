# Invitation flow

## Goal

A member of a not-yet-full household can generate one signed, expiring
invite link. Opening a valid link (after logging in or signing up) joins
the opener as the second member. Links to a full household, or opened by
someone who already has a household, are rejected with a clear message.

## Acceptance criteria

- [ ] `Invitation` model in `chores/models.py`, with a migration: FK `household`,
      FK `created_by` -> `settings.AUTH_USER_MODEL` (the inviting user),
      `created_at`, nullable `accepted_by` -> `settings.AUTH_USER_MODEL`, nullable
      `accepted_at`. One invitation per household (a `OneToOneField` on
      `household`, or a unique constraint plus `get_or_create`). The URL token is
      produced with `django.core.signing` over the invitation's pk; no raw token
      string is stored on the row.
- [ ] The `chores` URLconf gains two routes under `/household/`:
      `chores:invite` at `household/invite/` (the page that shows the link) and
      `chores:invite_accept` at `household/join/<token>/` (the link target).
- [ ] `GET /household/invite/` for a member of a one-person household
      get-or-creates that household's single `Invitation` and shows a shareable
      absolute URL for `chores:invite_accept` (built with
      `request.build_absolute_uri`) containing the signed token. Reloading the
      page shows the same link, not a second invitation.
- [ ] `GET /household/invite/` for a member of a two-person household shows
      "This household is already full." and offers no link.
- [ ] `GET /household/invite/` redirects an anonymous visitor to login, and
      redirects a signed-in user with no household to `chores:home` with a
      message (they have no household to invite anyone to).
- [ ] A member of a not-yet-full household sees an "Invite your partner" link in
      the header nav pointing at `chores:invite`. A member of a full household, a
      signed-in user with no household, and an anonymous visitor do not.
- [ ] A token older than `INVITATION_MAX_AGE_DAYS` (default 7, set in
      `config/settings.py` and read by the accept view) is rejected with "This
      invite has expired." and creates nothing.
- [ ] Opening a valid link while logged out redirects to login with `?next=` set
      to the invite-accept URL (via `LoginRequiredMixin` or an explicit
      redirect); after logging in the user returns to the invite-accept URL and
      the join completes.
- [ ] The same logged-out flow also works through signup: the login page's
      "Sign up" link carries the `next` parameter forward, and `SignupView`
      redirects to a safe `next` after creating the account (validated with
      `django.utils.http.url_has_allowed_host_and_scheme`), falling back to
      `chores:home` when `next` is absent. The existing signup and login tests
      still pass.
- [ ] Opening a valid link as a signed-in user with no household adds them as the
      second `Membership`, sets `accepted_by` / `accepted_at`, and redirects to
      `chores:home` with a welcome message. The membership creation and the
      invitation update run in one `transaction.atomic` block and reuse the
      task #5 "at most 2 members" guard (no second copy of the rule).
- [ ] Opening any link for a household that already has two members creates
      nothing and shows "This household is already full."
- [ ] Opening a link as a user who already belongs to a household - including the
      inviter opening their own household's link - creates nothing and shows a
      clear message, with no stack trace.
- [ ] A tampered, malformed, or unknown-pk token yields a 404 or a clean error
      page - never a stack trace.
- [ ] `Invitation` is registered in the admin with a useful `list_display`
      (household, `created_by`, `created_at`, `accepted_by`, `accepted_at`).
- [ ] Tests in `chores/tests/` cover each bullet above.
- [ ] `uv run pytest` and `uv run python manage.py check` pass.

## Out of scope

- Emailing the invite - the MVP shares the link manually
  (`_docs/tech-stack-decision.md`: "signed invite links; no email
  infrastructure for the MVP").
- Revoking or regenerating an outstanding invite, and any "resend" affordance -
  follow-up:
  [#26](https://github.com/ckcabang/household-chores/issues/26) (Revoke and regenerate invitations).
- More than one pending invitation per household - a two-person household needs
  only one.
- Seeding a `FairnessWeights` row for the now-complete household - task #12 owns
  that step and its test.

## Constraints

- Use `django.core.signing` (`TimestampSigner`, or `dumps`/`loads` with
  `max_age`); do not hand-roll token generation or expiry.
- Build absolute URLs from the request (`request.build_absolute_uri`).
- Reuse the `Membership` "at most 2 memberships" guard from task #5; do not
  duplicate the rule.
- Invitation acceptance runs in `transaction.atomic`.
- Models in `chores/models.py`; views, URLs, and templates in the `chores` app;
  templates extend `chores/base.html`. Gate both views on authentication with
  `LoginRequiredMixin` (or equivalent).
- Any redirect to a `next` target must be validated with
  `url_has_allowed_host_and_scheme` - never redirect to an unvalidated value.
- No new dependencies.
