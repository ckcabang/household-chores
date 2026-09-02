from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Household


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
