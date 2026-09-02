# User accounts

## Goal

A visitor can create an account, sign in, and sign out using Django's
built-in auth. No household concepts are touched in this task.

## Acceptance criteria

- [ ] `GET /accounts/signup/` renders a form (username, password, password
      confirmation) that extends `chores/base.html`.
- [ ] Posting valid, matching credentials creates a `User`, logs them in, and
      redirects to `chores:home`.
- [ ] Posting an invalid form (duplicate username, password mismatch, or a
      password rejected by `AUTH_PASSWORD_VALIDATORS`) re-renders the form with
      the error visible and creates no user.
- [ ] `GET /accounts/login/` renders a login form; valid credentials log in and
      redirect to `chores:home`, invalid credentials re-render with an error and
      no session.
- [ ] `POST /accounts/logout/` ends the session and redirects to `chores:home`.
- [ ] An authenticated user opening `/accounts/signup/` or `/accounts/login/` is
      redirected to `chores:home` without seeing the form.
- [ ] The header nav shows "Log in" / "Sign up" when logged out, and the
      username plus a "Log out" control when logged in.
- [ ] `chores/tests/` covers: signup success, duplicate-username rejection,
      password-mismatch rejection, login success, login failure, logout, and the
      authenticated-user redirect.
- [ ] `uv run pytest` and `uv run python manage.py check` pass.

## Out of scope

- Password reset / change flows — need email infrastructure, which the MVP
  excludes (`_docs/plan.md`, "Notifications: None in MVP"). Follow-up:
  [#22](https://github.com/ckcabang/household-chores/issues/22) (Password reset flow).
- Storing and verifying an email address on signup — follow-up:
  [#23](https://github.com/ckcabang/household-chores/issues/23) (Collect and verify email on signup).
- Rate limiting or lockout after repeated failed logins — follow-up:
  [#24](https://github.com/ckcabang/household-chores/issues/24) (Throttle failed login attempts).
- Any `Household` / `Membership` creation or onboarding redirect — task #5.

## Constraints

- Use `django.contrib.auth`: `UserCreationForm` (or a thin subclass),
  `LoginView`, `LogoutView`. Do **not** introduce a custom user model.
- Auth routes mounted under `/accounts/` in `config/urls.py`; forms, views, and
  templates live in the `chores` app. Put auth templates where the built-in
  views look for them (`registration/login.html`) or pass `template_name`.
- Templates extend `chores/base.html`.
- Set `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`, and `LOGIN_URL` in
  `config/settings.py`.
- No new dependencies.
