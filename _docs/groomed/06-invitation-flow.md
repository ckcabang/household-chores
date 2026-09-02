# Invitation flow

## Goal

A member of a not-yet-full household can generate one signed, expiring
invite link. Opening a valid link (after logging in or signing up) joins
the opener as the second member. Links to a full household are rejected
with a clear message.

## Acceptance criteria

- [ ] `Invitation` model: FK `household`, FK `created_by` (membership or user),
      `created_at`, nullable `accepted_by` / `accepted_at`. The token is signed
      with `django.core.signing` and not stored in plaintext (store a hash, or
      derive the token and store nothing).
- [ ] `GET /household/invite/`, for a member of a one-person household, shows a
      shareable absolute URL containing the signed token.
- [ ] The same page, for a member of a two-person household, shows "This
      household is already full." and offers no link.
- [ ] A token older than a configured max age (default 7 days, documented) is
      rejected with "This invite has expired."
- [ ] Opening a valid link while logged out routes through login / signup and
      then back to acceptance.
- [ ] Opening a valid link as a user with no household adds them as the second
      `Membership` and redirects to `chores:home` with a welcome message.
- [ ] Opening any link for a household that already has two members creates
      nothing and shows "This household is already full."
- [ ] Opening a link as a user who already has a household creates nothing and
      shows a clear error.
- [ ] A tampered or malformed token yields a 404 or a clean error page — never a
      stack trace.
- [ ] `Invitation` is registered in the admin.
- [ ] Tests cover each bullet above.

## Out of scope

- Emailing the invite — the MVP shares the link manually
  (`_docs/tech-stack-decision.md`: "signed invite links; no email
  infrastructure for the MVP").
- Revoking or regenerating an outstanding invite — follow-up:
  [#26](https://github.com/ckcabang/household-chores/issues/26) (Revoke and regenerate invitations).
- More than one pending invitation per household — a two-person household needs
  only one.

## Constraints

- Use `django.core.signing.TimestampSigner` (or `dumps`/`loads` with `max_age`);
  do not hand-roll token generation or expiry.
- Build absolute URLs from the request (`request.build_absolute_uri`).
- Reuse the "at most 2 memberships" rule from task #5; do not duplicate it.
- Acceptance runs in `transaction.atomic`.
