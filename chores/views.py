from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import ChoreForm, HouseholdForm, SignupForm
from .models import Chore, Invitation, Membership


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
        return super().get_queryset().select_related("primary_owner__user")


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
    pass


class ChoreDeleteView(HouseholdScopedMixin, DeleteView):
    """Confirm (GET) then delete (POST) a chore in the current household."""

    model = Chore
    template_name = "chores/chore_confirm_delete.html"
    success_url = reverse_lazy("chores:chore_list")
