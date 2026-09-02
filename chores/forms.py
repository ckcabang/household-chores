from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Chore, Household, Membership


class SignupForm(UserCreationForm):
    """Account signup form.

    A thin subclass of Django's :class:`UserCreationForm` so the fields
    (username, password, password confirmation) and all validation -
    duplicate usernames, password mismatch, and ``AUTH_PASSWORD_VALIDATORS`` -
    come straight from ``django.contrib.auth``.
    """

    class Meta(UserCreationForm.Meta):
        pass


class HouseholdForm(forms.ModelForm):
    """Create form for a household - a single ``name`` field."""

    class Meta:
        model = Household
        fields = ["name"]

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Please enter a name for your household.")
        return name


class ChoreForm(forms.ModelForm):
    """Create / edit form for a chore.

    The owning ``household`` is supplied by the view rather than chosen in the
    form: it is bound to the instance here so ``Chore.clean()`` can check the
    ``primary_owner`` against it, and the ``primary_owner`` choices are limited
    to that household's memberships.
    """

    class Meta:
        model = Chore
        fields = [
            "name",
            "description",
            "cadence_days",
            "estimated_minutes",
            "difficulty",
            "primary_owner",
            "allows_multiple_contributors",
        ]

    def __init__(self, *args, household=None, **kwargs):
        super().__init__(*args, **kwargs)
        if household is not None:
            self.instance.household = household
            self.fields["primary_owner"].queryset = Membership.objects.filter(
                household=household
            ).select_related("user")
        self.fields["primary_owner"].required = False
        self.fields["description"].required = False

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Please enter a name for this chore.")
        return name
