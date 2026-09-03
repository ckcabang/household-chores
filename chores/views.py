from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from .fairness import propose_assignments, who_is_ahead, workload_value
from .services import (
    assignable_chores,
    household_constraints,
    household_params,
    household_workloads,
    recent_contribution,
)
from .ai import setup as ai_setup
from .ai.setup import (
    AISetupConfigError,
    PlanGenerationError,
    PlanValidationError,
)
from .forms import (
    ChoreForm,
    CompletionForm,
    HouseholdForm,
    SetupQuestionnaireForm,
    SignupForm,
    WeightProposalForm,
)
from .models import (
    CONSTRAINT_KIND_CHOICES,
    DIFFICULTY_CHOICES,
    OCCURRENCE_STATUS_ACTIVE,
    OCCURRENCE_STATUS_COMPLETED,
    PROPOSAL_STATUS_ACCEPTED,
    PROPOSAL_STATUS_DISMISSED,
    PROPOSAL_STATUS_PENDING,
    WEIGHT_PROPOSAL_STATUS_OPEN,
    AISetupDraft,
    Chore,
    ChoreOccurrence,
    Constraint,
    ContributionCredit,
    EstimateProposal,
    FairnessWeights,
    Invitation,
    Membership,
    WeightProposal,
)
from .proposals import generate_estimate_proposals


def _safe_next(request):
    """Return a request-local ``next`` target, or ``None`` if unsafe/absent."""
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return None


class HomeView(TemplateView):
    """Placeholder landing page that exercises the base layout."""

    template_name = "chores/home.html"


class SignupView(CreateView):
    """Create an account with Django's built-in user creation form.

    An authenticated visitor is bounced to the home page without seeing the
    form; a successful signup logs the new user in and redirects to a safe
    ``next`` target when one is supplied, otherwise to the home page.
    """

    form_class = SignupForm
    template_name = "registration/signup.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("chores:home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next"] = self.request.POST.get("next") or self.request.GET.get(
            "next", ""
        )
        return context

    def get_success_url(self):
        return _safe_next(self.request) or reverse("chores:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class HouseholdCreateView(LoginRequiredMixin, CreateView):
    """Let a signed-in user with no household create one and join it.

    A user who already belongs to a household is redirected home with an
    explanatory message, on both GET and POST, without creating anything.
    An anonymous visitor is redirected to login by ``LoginRequiredMixin``.
    """

    form_class = HouseholdForm
    template_name = "chores/household_form.html"
    success_url = reverse_lazy("chores:home")

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and Membership.objects.filter(user=request.user).exists()
        ):
            messages.info(
                request,
                "You already belong to a household, so you can't create another.",
            )
            return redirect("chores:home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            Membership.objects.create(user=self.request.user, household=self.object)
        return redirect(self.get_success_url())


class InviteView(LoginRequiredMixin, TemplateView):
    """Show a member of a not-yet-full household its single shareable link.

    A signed-in user with no household has nobody to invite, so they are
    redirected home with a message. An anonymous visitor is sent to login by
    ``LoginRequiredMixin``.
    """

    template_name = "chores/invite.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.membership = (
                Membership.objects.select_related("household")
                .filter(user=request.user)
                .first()
            )
            if self.membership is None:
                messages.info(
                    request,
                    "You need a household before you can invite anyone.",
                )
                return redirect("chores:home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        household = self.membership.household
        if household.is_full():
            context["household_full"] = True
            return context
        invitation, _ = Invitation.objects.get_or_create(
            household=household,
            defaults={"created_by": self.request.user},
        )
        context["invite_url"] = self.request.build_absolute_uri(
            reverse("chores:invite_accept", args=[invitation.token])
        )
        return context


class InviteAcceptView(LoginRequiredMixin, View):
    """Handle someone opening a shared invite link.

    ``LoginRequiredMixin`` routes an anonymous visitor through login/signup
    with ``?next=`` pointing back here, so the join completes once they are
    authenticated.
    """

    template_name = "chores/invite_accept.html"

    def _error(self, request, message):
        return render(request, self.template_name, {"error": message}, status=200)

    def get(self, request, token):
        max_age = timedelta(days=settings.INVITATION_MAX_AGE_DAYS)
        try:
            invitation = Invitation.from_token(token, max_age)
        except signing.SignatureExpired:
            return self._error(request, "This invite has expired.")
        except (signing.BadSignature, Invitation.DoesNotExist):
            raise Http404("Unknown or invalid invite.")

        household = invitation.household

        if Membership.objects.filter(user=request.user).exists():
            return self._error(
                request,
                "You already belong to a household, so you can't accept an invite.",
            )

        if household.is_full():
            return self._error(request, "This household is already full.")

        try:
            with transaction.atomic():
                Membership.objects.create(user=request.user, household=household)
                invitation.accepted_by = request.user
                invitation.accepted_at = timezone.now()
                invitation.save(update_fields=["accepted_by", "accepted_at"])
        except ValidationError:
            # Lost a race for the second seat between the check and the write.
            return self._error(request, "This household is already full.")

        messages.success(
            request,
            f"Welcome! You've joined {household.name}.",
        )
        return redirect("chores:home")


class HouseholdScopedMixin(LoginRequiredMixin):
    """Gate a view behind login + household membership and scope its data.

    - An anonymous visitor is sent to login by ``LoginRequiredMixin``.
    - A signed-in user with no ``Membership`` is redirected to
      ``chores:household_create`` (on both GET and POST).
    - ``self.membership`` / ``self.household`` are exposed to the view and
      template, and ``get_queryset`` is filtered to the current household.

    Reused by the chore views here and by later tasks (#8, #10, #14, #17).
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.membership = (
                Membership.objects.select_related("household")
                .filter(user=request.user)
                .first()
            )
            if self.membership is None:
                return redirect("chores:household_create")
            self.household = self.membership.household
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(household=self.household)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("current_household", self.household)
        context.setdefault("current_membership", self.membership)
        return context


class ChoreListView(HouseholdScopedMixin, ListView):
    """List the current household's chores."""

    model = Chore
    template_name = "chores/chore_list.html"
    context_object_name = "chores"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("primary_owner__user")
            .prefetch_related("constraints__membership__user")
        )


class ChoreFormViewMixin(HouseholdScopedMixin):
    """Shared wiring for the chore create and update views."""

    model = Chore
    form_class = ChoreForm
    template_name = "chores/chore_form.html"
    success_url = reverse_lazy("chores:chore_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["household"] = self.household
        return kwargs


class ChoreCreateView(ChoreFormViewMixin, CreateView):
    pass


class ChoreUpdateView(ChoreFormViewMixin, UpdateView):
    """Edit a chore and manage its people-to-chore constraints."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["constraints"] = self.object.constraints.select_related(
            "membership__user"
        )
        context["household_memberships"] = Membership.objects.filter(
            household=self.household
        ).select_related("user")
        context["constraint_kind_choices"] = CONSTRAINT_KIND_CHOICES
        return context


class ChoreDeleteView(HouseholdScopedMixin, DeleteView):
    """Confirm (GET) then delete (POST) a chore in the current household."""

    model = Chore
    template_name = "chores/chore_confirm_delete.html"
    success_url = reverse_lazy("chores:chore_list")


class ConstraintCreateView(HouseholdScopedMixin, View):
    """POST-only: mark a person preferred/excluded for a chore.

    Scoped to the current household by ``HouseholdScopedMixin``. A GET is
    rejected with 405 and mutates nothing. A ``chore_pk`` or submitted
    ``membership`` outside the household is a 404.
    """

    http_method_names = ["post"]

    def post(self, request, chore_pk):
        chore = get_object_or_404(Chore, pk=chore_pk, household=self.household)
        edit_url = reverse("chores:chore_edit", args=[chore.pk])

        kind = request.POST.get("kind") or ""
        if kind not in dict(CONSTRAINT_KIND_CHOICES):
            messages.error(
                request, "Choose whether the person is preferred or excluded."
            )
            return redirect(edit_url)

        membership_id = request.POST.get("membership") or ""
        if not membership_id:
            messages.error(request, "Choose a person for this constraint.")
            return redirect(edit_url)
        try:
            membership = Membership.objects.select_related("user").get(
                pk=membership_id, household=self.household
            )
        except (Membership.DoesNotExist, ValueError):
            raise Http404("No such person in this household.")

        if Constraint.objects.filter(chore=chore, membership=membership).exists():
            messages.error(
                request,
                f"{membership.user.username} already has a constraint on "
                f"{chore.name}. Delete it before adding a different one.",
            )
            return redirect(edit_url)

        constraint = Constraint(chore=chore, membership=membership, kind=kind)
        try:
            constraint.full_clean()
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect(edit_url)
        constraint.save()
        messages.success(
            request,
            f"Marked {membership.user.username} "
            f"{constraint.get_kind_display().lower()} for {chore.name}.",
        )
        return redirect(edit_url)


class ConstraintDeleteView(HouseholdScopedMixin, View):
    """POST-only: remove one constraint from a chore in the household."""

    http_method_names = ["post"]

    def post(self, request, chore_pk, pk):
        chore = get_object_or_404(Chore, pk=chore_pk, household=self.household)
        constraint = get_object_or_404(Constraint, pk=pk, chore=chore)
        constraint.delete()
        messages.success(request, "Constraint removed.")
        return redirect("chores:chore_edit", pk=chore.pk)


class SetupView(HouseholdScopedMixin, FormView):
    """Guided questions + free text -> a validated draft plan (task #18).

    Nothing is applied to the household here; the draft is reviewed and
    confirmed in task #19. The Anthropic call is isolated in
    ``chores.ai.setup`` and reached through ``ai_setup.generate_plan`` so tests
    inject a stub and CI needs no key.
    """

    template_name = "chores/setup.html"
    form_class = SetupQuestionnaireForm
    success_url = reverse_lazy("chores:setup")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_draft"] = (
            self.household.ai_setup_drafts.order_by("-created_at").first()
        )
        return context

    def form_valid(self, form):
        try:
            plan = ai_setup.generate_plan(
                form.answers(), form.cleaned_data["description"]
            )
        except AISetupConfigError:
            messages.error(
                self.request,
                "AI setup isn't configured yet - ANTHROPIC_API_KEY is missing.",
            )
            return self.form_invalid(form)
        except PlanValidationError:
            messages.error(
                self.request,
                "The AI response didn't match what we expected. Please try again.",
            )
            return self.form_invalid(form)
        except PlanGenerationError:
            messages.error(
                self.request,
                "Couldn't reach the AI service just now. Please try again shortly.",
            )
            return self.form_invalid(form)

        AISetupDraft.objects.create(
            household=self.household,
            raw_response=plan.raw,
            chores=plan.chores,
            constraints=plan.constraints,
            assignments=plan.assignments,
            reasoning=plan.reasoning,
        )
        messages.success(
            self.request, "Draft plan generated. Review it before applying."
        )
        return super().form_valid(form)


class DashboardView(HouseholdScopedMixin, TemplateView):
    """One read-mostly screen: upcoming occurrences, the fairness balance, and
    a short recent-contribution summary.

    The only mutation is the per-row "mark done" shortcut, which reuses
    ``OccurrenceCompleteView`` and returns here via ``?next=``.
    """

    template_name = "chores/dashboard.html"

    # Overdue occurrences plus everything due within this many days.
    WINDOW_DAYS = 14

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        today = timezone.localdate()
        horizon = today + timedelta(days=self.WINDOW_DAYS)

        context["occurrences"] = list(
            ChoreOccurrence.objects.filter(
                chore__household=self.household,
                status=OCCURRENCE_STATUS_ACTIVE,
                due_date__lte=horizon,
            )
            .select_related("chore", "chore__primary_owner__user")
            .order_by("due_date", "id")
        )

        memberships = list(
            self.household.memberships.select_related("user")
        )
        workloads = household_workloads(self.household, now)
        ahead_id = who_is_ahead(workloads)
        context["balance"] = [
            {
                "member": m,
                "workload": workloads.get(m.pk, 0.0),
                "is_ahead": m.pk == ahead_id,
            }
            for m in memberships
        ]
        context["balance_is_even"] = ahead_id is None

        summary = recent_contribution(self.household, now)
        context["contribution"] = [
            {
                "member": m,
                "completions": summary.get(m.pk, {}).get("completions", 0),
                "credits": summary.get(m.pk, {}).get("credits", 0),
            }
            for m in memberships
        ]
        context["history_is_empty"] = all(
            row["completions"] == 0 and row["credits"] == 0
            for row in context["contribution"]
        )
        context["dashboard_next"] = reverse("chores:dashboard")
        return context


class FairnessWeightsView(HouseholdScopedMixin, TemplateView):
    """Read-only view of the household's fairness weights.

    Direct editing was removed in task #16: changes now go through a
    :class:`WeightProposal` that both members approve. This screen shows the
    current values and links to the open proposal (or to create one).
    """

    template_name = "chores/fairness.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["weights"], _ = FairnessWeights.objects.get_or_create(
            household=self.household
        )
        context["open_proposal"] = self.household.weight_proposals.filter(
            status=WEIGHT_PROPOSAL_STATUS_OPEN
        ).first()
        return context


class _WeightProposalScopedMixin(HouseholdScopedMixin):
    def get_proposal(self, pk):
        return get_object_or_404(
            WeightProposal, pk=pk, household=self.household
        )


class WeightProposalCreateView(HouseholdScopedMixin, CreateView):
    """Propose new fairness weights, pre-filled with the current values.

    Blocked (redirect with a message) when the household already has an open
    proposal - only one at a time.
    """

    model = WeightProposal
    form_class = WeightProposalForm
    template_name = "chores/weight_proposal_form.html"

    def get(self, request, *args, **kwargs):
        blocked = self._blocked_redirect()
        return blocked or super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        blocked = self._blocked_redirect()
        return blocked or super().post(request, *args, **kwargs)

    def _blocked_redirect(self):
        existing = self.household.weight_proposals.filter(
            status=WEIGHT_PROPOSAL_STATUS_OPEN
        ).first()
        if existing:
            messages.info(
                self.request,
                "There's already an open weight proposal. Resolve it first.",
            )
            return redirect("chores:weight_proposal_detail", pk=existing.pk)
        return None

    def get_initial(self):
        weights, _ = FairnessWeights.objects.get_or_create(
            household=self.household
        )
        return {
            "time_weight": weights.time_weight,
            "difficulty_weight": weights.difficulty_weight,
            "decay_half_life_days": weights.decay_half_life_days,
        }

    def form_valid(self, form):
        form.instance.household = self.household
        form.instance.created_by = self.membership
        response = super().form_valid(form)
        # The proposer approves by creating it.
        self.object.approved_by.add(self.membership)
        messages.success(
            self.request,
            "Proposal created. It applies once the other member approves.",
        )
        return response

    def get_success_url(self):
        return reverse("chores:weight_proposal_detail", args=[self.object.pk])


class WeightProposalDetailView(_WeightProposalScopedMixin, DetailView):
    """Proposed vs current values and each member's approval state."""

    template_name = "chores/weight_proposal_detail.html"
    context_object_name = "proposal"

    def get_object(self, queryset=None):
        return self.get_proposal(self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        weights, _ = FairnessWeights.objects.get_or_create(
            household=self.household
        )
        context["weights"] = weights
        approved_ids = set(
            self.object.approved_by.values_list("id", flat=True)
        )
        context["approvals"] = [
            {"member": m, "approved": m.pk in approved_ids}
            for m in self.household.memberships.select_related("user")
        ]
        context["viewer_has_approved"] = self.membership.pk in approved_ids
        return context


class WeightProposalApproveView(_WeightProposalScopedMixin, View):
    """POST-only: record the acting member's approval; apply if both agree."""

    http_method_names = ["post"]

    def post(self, request, pk):
        proposal = self.get_proposal(pk)
        if not proposal.is_open:
            messages.info(request, "That proposal is already closed.")
            return redirect("chores:weight_proposal_detail", pk=proposal.pk)

        proposal.approved_by.add(self.membership)
        if proposal.is_fully_approved():
            proposal.apply()
            messages.success(request, "Both approved - fairness weights updated.")
        else:
            messages.success(
                request, "Approval recorded. Waiting for the other member."
            )
        return redirect("chores:weight_proposal_detail", pk=proposal.pk)


class WeightProposalRejectView(_WeightProposalScopedMixin, View):
    """POST-only: reject the proposal; weights are left unchanged."""

    http_method_names = ["post"]

    def post(self, request, pk):
        proposal = self.get_proposal(pk)
        if not proposal.is_open:
            messages.info(request, "That proposal is already closed.")
            return redirect("chores:weight_proposal_detail", pk=proposal.pk)

        proposal.reject()
        messages.success(request, "Proposal rejected. Weights unchanged.")
        return redirect("chores:weight_proposal_detail", pk=proposal.pk)


class RebalanceView(HouseholdScopedMixin, TemplateView):
    """Preview an automatic reassignment of upcoming chores. Writes nothing.

    Shows, per chore with an active occurrence, the current owner vs the owner
    the fairness algorithm would propose, plus the projected per-member balance
    before and after. Applying the proposal is follow-up #29.
    """

    template_name = "chores/rebalance.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        params = household_params(self.household)
        current = household_workloads(self.household, now)
        chores = assignable_chores(self.household, params)
        result = propose_assignments(
            chores, current, household_constraints(self.household)
        )

        memberships = {
            m.pk: m
            for m in self.household.memberships.select_related("user")
        }
        chore_objs = {
            c.pk: c
            for c in Chore.objects.filter(
                pk__in=[c.id for c in chores]
            ).select_related("primary_owner__user")
        }

        context["rows"] = [
            {
                "chore": chore_objs[p.chore_id],
                "current_owner": memberships.get(p.current_owner_id),
                "proposed_owner": memberships.get(p.proposed_owner_id),
                "unassignable": p.unassignable,
                "changed": (
                    not p.unassignable
                    and p.proposed_owner_id != p.current_owner_id
                ),
            }
            for p in result.proposals
        ]
        context["current_balance"] = [
            {"member": memberships[mid], "workload": current.get(mid, 0.0)}
            for mid in memberships
        ]
        context["projected_balance"] = [
            {"member": memberships[mid], "workload": result.projected.get(mid, 0.0)}
            for mid in memberships
        ]
        return context


class EstimateProposalListView(HouseholdScopedMixin, ListView):
    """Pending estimate-change proposals for the household, with accept/dismiss.

    The "Check for updates" button (a POST to ``estimate_proposal_refresh``)
    runs the learning pass across the household's chores.
    """

    template_name = "chores/estimate_proposals.html"
    context_object_name = "proposals"

    def get_queryset(self):
        return (
            EstimateProposal.objects.filter(
                chore__household=self.household,
                status=PROPOSAL_STATUS_PENDING,
            )
            .select_related("chore")
            .order_by("-created_at", "id")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["decided"] = (
            EstimateProposal.objects.filter(chore__household=self.household)
            .exclude(status=PROPOSAL_STATUS_PENDING)
            .select_related("chore", "decided_by__user")
            .order_by("-decided_at", "id")[:10]
        )
        return context


class EstimateProposalRefreshView(HouseholdScopedMixin, View):
    """POST-only: run the estimate-learning pass for the current household."""

    http_method_names = ["post"]

    def post(self, request):
        created = generate_estimate_proposals(self.household)
        if created:
            messages.success(
                request,
                f"Found {len(created)} chore(s) whose logged times suggest a "
                "new estimate.",
            )
        else:
            messages.info(
                request, "No estimate changes to propose right now."
            )
        return redirect("chores:estimate_proposal_list")


class _EstimateProposalDecisionView(HouseholdScopedMixin, View):
    """Shared 404 + already-decided handling for accept and dismiss."""

    http_method_names = ["post"]

    def get_proposal(self, pk):
        return get_object_or_404(
            EstimateProposal, pk=pk, chore__household=self.household
        )


class EstimateProposalAcceptView(_EstimateProposalDecisionView):
    """POST-only: apply a proposal's values to its chore. Either member may."""

    def post(self, request, pk):
        proposal = self.get_proposal(pk)
        if proposal.status != PROPOSAL_STATUS_PENDING:
            messages.info(request, "That proposal has already been decided.")
            return redirect("chores:estimate_proposal_list")

        chore = proposal.chore
        with transaction.atomic():
            chore.estimated_minutes = proposal.proposed_minutes
            if proposal.proposed_difficulty is not None:
                chore.difficulty = proposal.proposed_difficulty
            chore.full_clean()
            chore.save()
            proposal.status = PROPOSAL_STATUS_ACCEPTED
            proposal.decided_at = timezone.now()
            proposal.decided_by = self.membership
            proposal.save(update_fields=["status", "decided_at", "decided_by"])

        messages.success(
            request,
            f"Updated “{chore.name}” to {proposal.proposed_minutes} min.",
        )
        return redirect("chores:estimate_proposal_list")


class EstimateProposalDismissView(_EstimateProposalDecisionView):
    """POST-only: dismiss a proposal without touching the chore."""

    def post(self, request, pk):
        proposal = self.get_proposal(pk)
        if proposal.status != PROPOSAL_STATUS_PENDING:
            messages.info(request, "That proposal has already been decided.")
            return redirect("chores:estimate_proposal_list")

        proposal.status = PROPOSAL_STATUS_DISMISSED
        proposal.decided_at = timezone.now()
        proposal.decided_by = self.membership
        proposal.save(update_fields=["status", "decided_at", "decided_by"])
        messages.success(request, "Proposal dismissed.")
        return redirect("chores:estimate_proposal_list")


def _active_occurrences(household):
    """The current household's ``active`` occurrences, oldest due first."""
    return (
        ChoreOccurrence.objects.filter(
            chore__household=household,
            status=OCCURRENCE_STATUS_ACTIVE,
        )
        .select_related(
            "chore", "chore__primary_owner__user", "claimed_by__user"
        )
        .order_by("due_date", "id")
    )


class OccurrenceListView(HouseholdScopedMixin, ListView):
    """The current household's outstanding occurrences with a mark-done form."""

    template_name = "chores/occurrence_list.html"
    context_object_name = "occurrences"

    def get_queryset(self):
        return _active_occurrences(self.household)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("difficulty_choices", DIFFICULTY_CHOICES)
        return context


class OccurrenceCompleteView(HouseholdScopedMixin, View):
    """POST-only: mark an ``active`` occurrence done and record who did it.

    A GET is rejected with 405 and mutates nothing. An occurrence in another
    household - or an unknown pk - is a 404. Posting against an already
    ``completed`` occurrence is a no-op with an info message.
    """

    http_method_names = ["post"]

    def _done_redirect(self, request):
        """Back to a safe ``next`` (e.g. the dashboard) or the occurrence list."""
        return redirect(_safe_next(request) or reverse("chores:occurrence_list"))

    def post(self, request, pk):
        occurrence = get_object_or_404(
            ChoreOccurrence, pk=pk, chore__household=self.household
        )

        if occurrence.status == OCCURRENCE_STATUS_COMPLETED:
            messages.info(request, "That occurrence is already marked done.")
            return self._done_redirect(request)

        form = CompletionForm(request.POST)
        if not form.is_valid():
            context = {
                "occurrences": _active_occurrences(self.household),
                "current_household": self.household,
                "current_membership": self.membership,
                "difficulty_choices": DIFFICULTY_CHOICES,
                "complete_form": form,
                "complete_form_pk": occurrence.pk,
            }
            return render(
                request, "chores/occurrence_list.html", context, status=200
            )

        chore = occurrence.chore
        owner = chore.primary_owner

        with transaction.atomic():
            occurrence.status = OCCURRENCE_STATUS_COMPLETED
            occurrence.completed_at = timezone.now()
            occurrence.save(update_fields=["status", "completed_at"])
            completion = form.save(commit=False)
            completion.occurrence = occurrence
            completion.completed_by = self.membership
            completion.save()

            # Record helper credit when this member covered work owned by the
            # other member. Nothing to credit when the chore has no owner, or
            # when the owner did their own chore. ``workload_value`` is frozen
            # from the chore's estimate (not the Completion's actuals) with
            # neutral weights - task #12 wires in the household's real weights.
            if owner is not None and owner.pk != self.membership.pk:
                ContributionCredit.objects.get_or_create(
                    completion=completion,
                    defaults={
                        "helper": self.membership,
                        "owner": owner,
                        "workload_value": workload_value(
                            chore.estimated_minutes,
                            chore.difficulty,
                            weights=None,
                        ),
                    },
                )

        messages.success(
            request, f"Marked “{occurrence.chore.name}” done."
        )
        return self._done_redirect(request)


class OccurrenceClaimView(HouseholdScopedMixin, View):
    """POST-only: volunteer the acting member to do one ``active`` occurrence.

    Claiming is advisory - it sets ``occurrence.claimed_by`` and never touches
    ``chore.primary_owner``. A GET is rejected with 405 and mutates nothing. An
    occurrence in another household - or an unknown pk - is a 404.

    No-op paths (info message, nothing written): the acting member already owns
    the chore, the occurrence is already ``completed``, or the acting member has
    already claimed it. Claiming an occurrence the *other* member claimed
    reassigns it ("I'll take it instead").
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        occurrence = get_object_or_404(
            ChoreOccurrence, pk=pk, chore__household=self.household
        )
        list_url = reverse("chores:occurrence_list")

        if occurrence.chore.primary_owner_id == self.membership.pk:
            messages.info(request, "You already own that chore.")
            return redirect(list_url)

        if occurrence.status == OCCURRENCE_STATUS_COMPLETED:
            messages.info(request, "That occurrence is already marked done.")
            return redirect(list_url)

        if occurrence.claimed_by_id == self.membership.pk:
            messages.info(request, "You've already claimed that occurrence.")
            return redirect(list_url)

        occurrence.claimed_by = self.membership
        occurrence.save(update_fields=["claimed_by"])
        messages.success(
            request, f"You've claimed “{occurrence.chore.name}”."
        )
        return redirect(list_url)
