from django import forms
from django.contrib.auth.forms import UserCreationForm

from .fairness import weight_errors
from .models import (
    Chore,
    Completion,
    FairnessWeights,
    Household,
    Membership,
    WeightProposal,
)

# The fairness-weight fields, named once so the read-only settings screen
# (task #12) and the change-proposal form (task #16) stay in lock step with the
# ``WeightValues`` model base.
WEIGHT_FIELDS = ["time_weight", "difficulty_weight", "decay_half_life_days"]


class _WeightValuesForm(forms.ModelForm):
    """Shared validation for any form over the three ``WeightValues`` fields."""

    def clean(self):
        cleaned = super().clean()
        errors = weight_errors(
            cleaned.get("time_weight"),
            cleaned.get("difficulty_weight"),
            cleaned.get("decay_half_life_days"),
        )
        for field, message in errors.items():
            # A missing value already has its own "required" error - don't
            # stack a range error on top of it.
            if cleaned.get(field) is not None:
                self.add_error(field, message)
        return cleaned


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


class FairnessWeightsForm(_WeightValuesForm):
    """Bind the three weight fields against the stored ``FairnessWeights`` row.

    Used to apply an approved :class:`WeightProposal` (task #16) and by any
    admin/data path that needs the same validation as the proposal form.
    """

    class Meta:
        model = FairnessWeights
        fields = WEIGHT_FIELDS


class WeightProposalForm(_WeightValuesForm):
    """Propose new fairness weights. The household and creator are set by the
    view; approval and application happen on the model."""

    class Meta:
        model = WeightProposal
        fields = WEIGHT_FIELDS


class CompletionForm(forms.ModelForm):
    """Optional feedback captured when an occurrence is marked done.

    ``completed_by`` and ``occurrence`` are set by the view, never here. Both
    remaining fields are optional; when supplied they are validated against the
    model (``actual_minutes`` a positive int, ``actual_effort`` within the
    shared difficulty scale).
    """

    class Meta:
        model = Completion
        fields = ["actual_minutes", "actual_effort"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["actual_minutes"].required = False
        self.fields["actual_effort"].required = False
