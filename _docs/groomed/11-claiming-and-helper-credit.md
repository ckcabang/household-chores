# Claiming and helper credit

## Goal

When a member does a chore that another member owns — by claiming an
occurrence first, or by completing it directly — a `ContributionCredit`
row records that the helper covered work owned by the other member, with a
`workload_value` frozen at completion time. This task is accurate capture
only: it introduces the shared per-item workload function but does no
decay, balance, or assignment math.

## Acceptance criteria

### Claiming

- [ ] `ChoreOccurrence` gains `claimed_by` → `Membership`
      (`on_delete=SET_NULL`, `null=True`, `blank=True`,
      `related_name="claimed_occurrences"`). `clean()` rejects a `claimed_by`
      whose household is not the chore's household.
- [ ] New route `occurrences/<int:pk>/claim/`, URL name
      `chores:occurrence_claim`, `OccurrenceClaimView(HouseholdScopedMixin,
      View)` with `http_method_names = ["post"]`. A GET returns 405 and writes
      nothing. The occurrence is resolved with
      `get_object_or_404(ChoreOccurrence, pk=pk, chore__household=self.household)`,
      so another household's occurrence — or an unknown pk — is a 404. The POST
      is CSRF-protected.
- [ ] A claim POST by a member who is **not** the chore's `primary_owner`, on an
      `active` occurrence, sets `occurrence.claimed_by` to the acting membership
      (from `HouseholdScopedMixin`, never a form field), redirects to
      `chores:occurrence_list` with a success message, and leaves
      `chore.primary_owner` unchanged.
- [ ] Claiming an occurrence already claimed by the other member reassigns
      `claimed_by` to the acting member (a two-person household has no third
      party; this is the "I'll take it instead" path). Re-claiming an occurrence
      the acting member already claimed is an idempotent no-op with an info
      message.
- [ ] A claim POST is a no-op (info message, nothing written, redirect to
      `chores:occurrence_list`) when the acting member is the chore's
      `primary_owner` ("you already own that chore"), or the occurrence is
      already `completed`.
- [ ] Login / household gating comes from `HouseholdScopedMixin`: an anonymous
      visitor is redirected to login; a signed-in user with no `Membership` is
      redirected to `chores:household_create`.

### Credit capture

- [ ] `ContributionCredit` model in `chores/models.py`, with a migration:
      `OneToOneField` to `Completion` (`related_name="credit"`,
      `on_delete=CASCADE`); FK `helper` → `Membership`
      (`on_delete=PROTECT`, `related_name="credits_as_helper"`); FK `owner` →
      `Membership` (`on_delete=PROTECT`, `related_name="credits_as_owner"`);
      `workload_value` (`FloatField`); `created_at` (`auto_now_add`). The
      occurrence is reachable as `credit.completion.occurrence` — no separate
      occurrence FK.
- [ ] Completing an occurrence whose chore has a `primary_owner` that is **not**
      the acting member (the task #10 path, whether or not the occurrence was
      claimed first) creates exactly one `ContributionCredit` with
      `helper` = the acting membership, `owner` = the chore's `primary_owner`,
      and `workload_value` = `chores.fairness.workload_value(...)` (see below).
      The credit is written inside the same `transaction.atomic` block that
      flips the occurrence and writes the `Completion`, via `get_or_create`
      keyed on the `Completion`.
- [ ] No `ContributionCredit` is created when the acting member **is** the
      chore's `primary_owner`, or when the chore has **no** `primary_owner`
      (nobody's work was covered).
- [ ] `workload_value` is computed from the **chore's estimate** —
      `chore.estimated_minutes` and `chore.difficulty` — not from the
      `Completion`'s optional `actual_minutes` / `actual_effort`, even when
      those are supplied. It is frozen on the row once written.
- [ ] `helper` and `owner` are always two distinct memberships: a
      `CheckConstraint` (`~Q(helper=F("owner"))`, named
      `contributioncredit_helper_ne_owner`) plus `ContributionCredit.clean()`
      reject a self-owned credit (`helper_id == owner_id`); `clean()` also
      rejects a `helper`/`owner` pair from different households.
- [ ] One completion yields at most one credit: re-POSTing "mark done" on an
      already-`completed` occurrence stays a no-op (per #10) and adds no second
      credit; the `OneToOneField` on `Completion` and the `get_or_create` make
      this structural.

### Shared workload function

- [ ] A framework-agnostic `chores/fairness/` package is created here:
      `chores/fairness/__init__.py` re-exporting the public API, and
      `chores/fairness/workload.py` holding `WorkloadWeights` and
      `workload_value`. No module in the package imports from `django.*` or
      `chores.models`.
- [ ] `WorkloadWeights` is a frozen dataclass with documented neutral defaults
      `time_weight: float = 1.0` and `difficulty_weight: float = 1.0`.
- [ ] `workload_value(estimated_minutes: int, difficulty: int, weights:
      WorkloadWeights | None = None) -> float` returns, with a formula
      documented in the module docstring:

      ```
      BASELINE_DIFFICULTY = 3            # "Moderate" on DIFFICULTY_CHOICES
      DIFFICULTY_MIN, DIFFICULTY_MAX = 1, 5

      w = weights or WorkloadWeights()
      difficulty_factor = 1.0 + w.difficulty_weight * (
          (difficulty - BASELINE_DIFFICULTY) / (DIFFICULTY_MAX - DIFFICULTY_MIN)
      )
      return w.time_weight * estimated_minutes * difficulty_factor
      ```

      Worked, with default weights: `workload_value(30, 3) == 30.0`,
      `workload_value(30, 5) == 45.0`, `workload_value(20, 1) == 10.0`.
- [ ] `BASELINE_DIFFICULTY`, `DIFFICULTY_MIN`, `DIFFICULTY_MAX` are defined
      locally in `chores/fairness/workload.py` (the package stays Django-free); a
      test asserts they match `chores.models.DIFFICULTY_MIN` /
      `DIFFICULTY_MAX` and the `"Moderate"` value in `DIFFICULTY_CHOICES` so the
      two definitions cannot drift.
- [ ] `import chores.fairness` triggers no Django settings access; the fairness
      unit tests run without a database.

### Admin

- [ ] `ContributionCredit` is registered in `chores/admin.py` with
      `list_display = ("completion", "helper", "owner", "workload_value",
      "created_at")`, `list_select_related =
      ("completion__occurrence__chore", "helper__user", "owner__user")`,
      `list_filter = ("helper__household",)`, and `search_fields` over the chore
      name and both usernames.
- [ ] `ChoreOccurrenceAdmin` adds `"claimed_by"` to `list_display` and
      `"claimed_by__user"` to `list_select_related`.

### UI

- [ ] The `/occurrences/` list from #10 (`chores/occurrence_list.html`) gains,
      per `active` row: a "Claim" button (a CSRF-protected POST form to
      `chores:occurrence_claim`) shown only when the current member is **not**
      the chore's `primary_owner` and has not already claimed that occurrence;
      and, when `occurrence.claimed_by` is set, a "Claimed by <username>"
      indicator. The owner's own rows show no Claim button. No new list page and
      no new nav link — this reuses the page #10 added.

### Gate

- [ ] Tests in `chores/tests/` cover: non-owner completion → one credit with the
      expected `workload_value`; owner completing their own occurrence → no
      credit; chore with no `primary_owner`, non-owner completes → no credit;
      claim then complete by the claimer → credit and `claimed_by` set;
      re-POST complete on a completed occurrence → still one credit, no error;
      `ContributionCredit.full_clean()` with `helper == owner` raises and the DB
      `CheckConstraint` rejects it; non-owner claim sets `claimed_by` and leaves
      `primary_owner` unchanged; claim of own / completed / cross-household /
      unknown-pk occurrence handled as specified; GET on the claim URL is 405;
      no-household redirect on the claim view; `workload_value` worked examples
      (including an explicit `WorkloadWeights`); `import chores.fairness` does no
      Django settings access and the local difficulty bounds match
      `chores.models`; the Claim button visibility condition in the list
      template.
- [ ] `uv run pytest` and `uv run python manage.py check` pass.

## Out of scope

- Passing the household's real `FairnessWeights` into `workload_value` — the
  completion path uses `WorkloadWeights()` neutral defaults until then — and any
  recompute or backfill of `workload_value` on credits written before weights
  existed: task **#12** (which builds the `FairnessWeights` model and adapts it
  into `WorkloadWeights`).
- Time-decay, per-member workload/balance, and spending credits into assignment:
  tasks **#13** (workload with decay — its per-item step reuses
  `workload_value` from this task) and **#14** (assignment).
- Restricting who may complete a claimed occurrence to the claimer, and any
  reminder/nudge about claimed-but-not-done work — not in the MVP.
- Undoing a completion (and the credit it created): follow-up
  [#28](https://github.com/ckcabang/household-chores/issues/28).
- Non-goal (not deferred): clearing a claim back to nobody. In a two-person
  household the other member can simply claim the occurrence instead, which
  reassigns `claimed_by`; a standalone "un-claim" is unnecessary.

## Constraints

- `ContributionCredit` and the `ChoreOccurrence.claimed_by` field live in
  `chores/models.py`; one migration for both.
- The per-item workload derivation is the single pure function
  `chores.fairness.workload_value` (in `chores/fairness/workload.py`, re-exported
  from `chores/fairness/__init__.py`). No `django.*` or `chores.models` imports
  anywhere in `chores/fairness/`. Capture here and the later math (#12, #13) all
  go through this one function so they cannot drift. No workload arithmetic in
  the view or model beyond calling it.
- Claim and complete views are class-based in `chores/views.py` using the shared
  `HouseholdScopedMixin`; POST-only, CSRF-protected, resolving the occurrence
  with `get_object_or_404(ChoreOccurrence, pk=pk, chore__household=self.household)`.
- Add the claim route to the `chores` URLconf as
  `occurrences/<int:pk>/claim/` → `chores:occurrence_claim`. Reuse
  `chores/occurrence_list.html` and the existing "Occurrences" nav link from
  #10.
- Credit creation happens inside the existing `transaction.atomic` block in
  `OccurrenceCompleteView`, via `get_or_create` keyed on the `Completion`.
- `_active_occurrences` (or the list view queryset) adds
  `select_related("claimed_by__user")` for the new indicator.
- No new dependencies.
