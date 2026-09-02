# Completing an occurrence

## Goal

A member can see their household's outstanding occurrences on a simple list
page and mark an active one done, optionally recording actual time and
effort. A `Completion` row captures who did it and the logged values — the
raw data later consumed by fairness and estimate learning.

## Acceptance criteria

- [ ] `Completion` model in `chores/models.py`, with a migration:
      `OneToOneField` to `ChoreOccurrence` (`related_name="completion"`,
      `on_delete=CASCADE`), FK `completed_by` → `Membership`
      (`on_delete=PROTECT` or `SET_NULL`+nullable — pick one and note it),
      nullable `actual_minutes` (positive int; `MinValueValidator(1)`),
      nullable `actual_effort` (small int; `choices=DIFFICULTY_CHOICES` so it
      shares the chore difficulty scale), `created_at` (`auto_now_add`).
- [ ] A minimal occurrences list page is added by this task:
      `GET /occurrences/` (URL name `chores:occurrence_list`,
      `OccurrenceListView(HouseholdScopedMixin, ListView)`, template
      `chores/occurrence_list.html` extending `chores/base.html`). It lists the
      current household's `active` occurrences (including ones whose
      `is_overdue` is `True`), ordered by `due_date`, showing chore name, due
      date, owner, and an `overdue` marker; occurrences of other households
      never appear. `completed` occurrences are not shown. An empty list
      renders a clean "nothing due" state.
- [ ] Each listed occurrence has an inline "mark done" form that POSTs to
      `chores:occurrence_complete` at `/occurrences/<int:pk>/complete/`
      (`OccurrenceCompleteView(HouseholdScopedMixin, View)`,
      `http_method_names = ["post"]`; a GET returns 405 and mutates nothing).
      The form is CSRF-protected and carries the two optional actual fields
      (`actual_minutes`, `actual_effort`).
- [ ] A "mark done" POST on an `active` occurrence sets `status=completed` and
      `completed_at=timezone.now()`, and creates the `Completion` with
      `completed_by` = the acting member's `Membership` (from
      `HouseholdScopedMixin`, never a form field). Flipping the occurrence and
      writing the `Completion` happen inside one `transaction.atomic` block. On
      success it redirects back to `chores:occurrence_list` with a success
      message.
- [ ] Optional actual values: `actual_minutes` and `actual_effort` are read
      from the same POST via a `CompletionForm` (`ModelForm` on `Completion`,
      both fields `required=False`). When omitted, the `Completion` is created
      with them null. When present they must be valid (`actual_minutes` a
      positive int; `actual_effort` within `DIFFICULTY_CHOICES`, i.e.
      `DIFFICULTY_MIN`–`DIFFICULTY_MAX`) — otherwise the occurrence list
      re-renders (HTTP 200) with the form's field errors shown for that
      occurrence and nothing is written (no status change, no `Completion`).
- [ ] Posting "mark done" on an already-`completed` occurrence is a no-op: it
      adds an info message, creates no second `Completion`, changes nothing,
      and redirects to `chores:occurrence_list` (not a 404, not a 500).
- [ ] Only members of the occurrence's household can complete it: the view
      resolves the occurrence with
      `get_object_or_404(ChoreOccurrence, pk=pk, chore__household=self.household)`,
      so any other household's occurrence — or an unknown pk — is a 404.
- [ ] Login / household gating comes from `HouseholdScopedMixin`: an anonymous
      visitor is redirected to login; a signed-in user with no `Membership` is
      redirected to `chores:household_create`, on both the list and the
      complete view.
- [ ] The header nav in `chores/base.html` shows an "Occurrences" link
      pointing at `chores:occurrence_list`, under the same
      `{% if current_household %}` condition as the existing "Chores" link
      (hidden for anonymous visitors and signed-in users with no household).
      Update the placeholder comment in `base.html` accordingly.
- [ ] `Completion` is registered in `chores/admin.py` with
      `list_display = ("occurrence", "completed_by", "actual_minutes",
      "actual_effort", "created_at")`, `list_select_related` for `occurrence`
      and `completed_by__user`, and a `completed_by__household` `list_filter`.
- [ ] HTMX is optional: the plain full-page POST → redirect flow works and is
      what the tests exercise. An engineer may additionally enhance the inline
      form with `hx-post` for an in-place row update, but no acceptance
      criterion or test depends on it.
- [ ] Tests in `chores/tests/` cover: occurrence list scoping (only this
      household's `active` occurrences, overdue flag shown), complete without
      feedback, complete with feedback (actual values stored), double-complete
      guarded (no second `Completion`, no error), cross-household 404, invalid
      actual values (list re-renders with errors, nothing written), GET on the
      complete URL is 405, the no-household redirect, and the "Occurrences" nav
      link visibility condition.
- [ ] `uv run pytest` and `uv run python manage.py check` pass.

## Out of scope

- The combined dashboard view (upcoming occurrences with fairness balance and
  contribution history) — task #17. #17 builds the richer landing page and its
  "mark done" shortcut **reuses `chores:occurrence_complete` from this task**;
  it may also fold or link the plain `/occurrences/` list. This task ships the
  minimal list so #10 is testable on its own before #17 lands.
- A non-owner completion creating contribution credit — task #11 (it will hook
  into the same `OccurrenceCompleteView` / `Completion` write).
- Undoing or reopening a completion — follow-up:
  [#28](https://github.com/ckcabang/household-chores/issues/28) (Undo a completion).
- Any fairness or estimate math over completions — tasks #13 and #15.
- A per-occurrence detail page — not needed; the list row is the whole UI.

## Constraints

- Model in `chores/models.py`; the effort scale is the existing
  `DIFFICULTY_CHOICES` constant (with `DIFFICULTY_MIN` / `DIFFICULTY_MAX`) from
  task #7, not a new constant.
- Class-based views in `chores/views.py` using the shared
  `HouseholdScopedMixin` (introduced by task #7); `CompletionForm` in
  `chores/forms.py`; templates in the `chores` app extending
  `chores/base.html`, mirroring the existing chore templates.
- Add the two routes under `/occurrences/` in the `chores` URLconf with the URL
  names above, and the "Occurrences" nav link in `chores/base.html`.
- Flipping the occurrence and writing the `Completion` happen in one
  `transaction.atomic` block.
- No new dependencies.
