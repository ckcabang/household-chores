from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from .forms import HouseholdForm, SignupForm
from .models import Membership


class HomeView(TemplateView):
    """Placeholder landing page that exercises the base layout."""

    template_name = "chores/home.html"


class SignupView(CreateView):
    """Create an account with Django's built-in user creation form.

    An authenticated visitor is bounced to the home page without seeing the
    form; a successful signup logs the new user in and redirects there too.
    """

    form_class = SignupForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("chores:home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("chores:home")
        return super().dispatch(request, *args, **kwargs)

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
