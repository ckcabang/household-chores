from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

# A household is permanently capped at two people (see _docs/plan.md).
MAX_MEMBERS_PER_HOUSEHOLD = 2

# The fixed difficulty scale for a chore. Defined here as a plain list of
# ``(value, label)`` pairs - NOT ``models.IntegerChoices`` - so the
# framework-agnostic ``chores/fairness/`` module and task #10's effort field
# can import it without pulling in Django's model layer.
DIFFICULTY_CHOICES = [
    (1, "Very easy"),
    (2, "Easy"),
    (3, "Moderate"),
    (4, "Hard"),
    (5, "Very hard"),
]

# Convenience bounds derived from the scale above.
DIFFICULTY_MIN = DIFFICULTY_CHOICES[0][0]
DIFFICULTY_MAX = DIFFICULTY_CHOICES[-1][0]

# The two ways a household can mark a person against a chore. Defined here as a
# plain list of ``(value, label)`` pairs - NOT ``models.TextChoices`` - mirroring
# ``DIFFICULTY_CHOICES`` so the framework-agnostic ``chores/fairness/`` package
# (task #13) and the assignment algorithm (#14) can import the values without
# pulling in Django's model layer.
CONSTRAINT_KIND_CHOICES = [
    ("prefer", "Preferred"),
    ("exclude", "Excluded"),
]

# The lifecycle states a single dated chore occurrence moves through. Defined
# here as a plain list of ``(value, label)`` pairs - NOT ``models.TextChoices`` -
# mirroring ``CONSTRAINT_KIND_CHOICES`` so the framework-light
# ``chores/occurrences.py`` module and task #10's completion flow can import the
# values without pulling in Django's model layer.
OCCURRENCE_STATUS_CHOICES = [
    ("active", "Active"),
    ("completed", "Completed"),
]

OCCURRENCE_STATUS_ACTIVE = OCCURRENCE_STATUS_CHOICES[0][0]
OCCURRENCE_STATUS_COMPLETED = OCCURRENCE_STATUS_CHOICES[1][0]

# Namespace for the signed invitation tokens so they can't be swapped in
# from another ``django.core.signing`` use.
INVITATION_TOKEN_SALT = "chores.models.Invitation"


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


class Invitation(models.Model):
    """A single pending invite for a not-yet-full household.

    The shareable URL carries a :mod:`django.core.signing` token over this
    row's primary key - the token string itself is never stored. One
    invitation per household is enforced by the ``OneToOneField``.
    """

    household = models.OneToOneField(
        Household,
        on_delete=models.CASCADE,
        related_name="invitation",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invitations_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitations_accepted",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Invitation to {self.household}"

    @property
    def token(self):
        """A signed, URL-safe token identifying this invitation."""
        return signing.dumps(self.pk, salt=INVITATION_TOKEN_SALT)

    @staticmethod
    def from_token(token, max_age):
        """Return the ``Invitation`` a token points at.

        Raises :class:`signing.SignatureExpired` if the token is older than
        ``max_age`` (a ``timedelta`` or seconds), :class:`signing.BadSignature`
        if it is tampered or malformed, and :class:`Invitation.DoesNotExist`
        if the signed pk no longer exists.
        """
        pk = signing.loads(token, salt=INVITATION_TOKEN_SALT, max_age=max_age)
        return Invitation.objects.get(pk=pk)


class Chore(models.Model):
    """A recurring task a household plans and shares.

    Occurrences are generated from ``cadence_days`` by a later task (#9); this
    model only captures the chore's definition.
    """

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="chores",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cadence_days = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="How many days between one occurrence and the next.",
    )
    estimated_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Rough time one occurrence takes.",
    )
    difficulty = models.PositiveSmallIntegerField(
        choices=DIFFICULTY_CHOICES,
        default=DIFFICULTY_CHOICES[2][0],
    )
    primary_owner = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_chores",
    )
    allows_multiple_contributors = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if (
            self.primary_owner_id is not None
            and self.household_id is not None
            and self.primary_owner.household_id != self.household_id
        ):
            raise ValidationError(
                {
                    "primary_owner": (
                        "The primary owner must be a member of this household."
                    )
                }
            )

    def constraints_summary(self):
        """A short per-row summary of this chore's constraints for the list.

        Reads from ``self.constraints`` so a caller can ``prefetch_related`` it.
        """
        parts = [
            f"{c.membership.user.username}: {c.get_kind_display().lower()}"
            for c in self.constraints.all()
        ]
        return ", ".join(parts) if parts else "None"


class Constraint(models.Model):
    """Either member's mark that a person is preferred or excluded for a chore.

    This model is storage plus management UI only; the assignment algorithm
    (task #14) reads these records when it schedules occurrences.
    """

    chore = models.ForeignKey(
        Chore,
        on_delete=models.CASCADE,
        related_name="constraints",
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name="constraints",
    )
    kind = models.CharField(max_length=20, choices=CONSTRAINT_KIND_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["chore", "membership"],
                name="unique_constraint_per_person_per_chore",
            ),
        ]

    def __str__(self):
        return (
            f"{self.membership.user} "
            f"{self.get_kind_display().lower()} for {self.chore}"
        )

    def clean(self):
        super().clean()
        if (
            self.chore_id is not None
            and self.membership_id is not None
            and self.chore.household_id != self.membership.household_id
        ):
            raise ValidationError(
                {
                    "membership": (
                        "The person and the chore must belong to the "
                        "same household."
                    )
                }
            )


class ChoreOccurrence(models.Model):
    """One dated instance of a chore, generated from the chore's cadence.

    Rows are created by ``chores/occurrences.py`` (task #9). ``completed_at`` is
    declared here but only written when an occurrence is completed (task #10).
    Whether an occurrence is overdue is never stored - see :attr:`is_overdue`.
    """

    chore = models.ForeignKey(
        Chore,
        on_delete=models.CASCADE,
        related_name="occurrences",
    )
    due_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=OCCURRENCE_STATUS_CHOICES,
        default=OCCURRENCE_STATUS_ACTIVE,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["chore", "due_date"],
                name="unique_occurrence_per_chore_per_date",
            ),
        ]

    def __str__(self):
        return f"{self.chore} on {self.due_date}"

    @property
    def is_overdue(self):
        """True for an ``active`` occurrence whose ``due_date`` is in the past.

        Derived on read - there is no stored ``overdue`` field. A ``completed``
        occurrence is never overdue.
        """
        if self.status != OCCURRENCE_STATUS_ACTIVE:
            return False
        return self.due_date < timezone.localdate()


class Completion(models.Model):
    """The record that an occurrence was done: who did it and any logged actuals.

    One row per occurrence (``OneToOneField``). ``actual_minutes`` /
    ``actual_effort`` are optional feedback - the raw data later consumed by
    fairness (task #13) and estimate learning (task #15). ``actual_effort``
    reuses the chore ``DIFFICULTY_CHOICES`` scale rather than a new one.

    ``completed_by`` uses ``on_delete=PROTECT``: a membership that has completed
    something can't be deleted out from under its completion history.
    """

    occurrence = models.OneToOneField(
        ChoreOccurrence,
        on_delete=models.CASCADE,
        related_name="completion",
    )
    completed_by = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="completions",
    )
    actual_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="How long it actually took, if recorded.",
    )
    actual_effort = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=DIFFICULTY_CHOICES,
        help_text="How hard it actually was, on the chore difficulty scale.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self):
        return f"{self.occurrence} done by {self.completed_by.user}"
