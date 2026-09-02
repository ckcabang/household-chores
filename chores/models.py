from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

# A household is permanently capped at two people (see _docs/plan.md).
MAX_MEMBERS_PER_HOUSEHOLD = 2


class Household(models.Model):
    """A two-person unit that chores are planned and shared within."""

    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def member_count(self):
        return self.memberships.count()

    def is_full(self):
        return self.member_count() >= MAX_MEMBERS_PER_HOUSEHOLD


class Membership(models.Model):
    """Links one user to the single household they belong to."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                name="unique_membership_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user} in {self.household}"

    def _assert_household_not_full(self):
        """The single source of truth for the 'at most two members' rule.

        Called from both :meth:`clean` (so admin forms surface it) and
        :meth:`save` (so programmatic creation from the view or shell is
        guarded too).
        """
        if self.household_id is None:
            return
        siblings = Membership.objects.filter(household_id=self.household_id)
        if self.pk:
            siblings = siblings.exclude(pk=self.pk)
        if siblings.count() >= MAX_MEMBERS_PER_HOUSEHOLD:
            raise ValidationError(
                f"A household can have at most {MAX_MEMBERS_PER_HOUSEHOLD} members."
            )

    def clean(self):
        super().clean()
        self._assert_household_not_full()

    def save(self, *args, **kwargs):
        self._assert_household_not_full()
        super().save(*args, **kwargs)
