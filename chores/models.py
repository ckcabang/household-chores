from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from .fairness import (
    DEFAULT_DECAY_HALF_LIFE_DAYS,
    DEFAULT_DIFFICULTY_WEIGHT,
    DEFAULT_TIME_WEIGHT,
    HALF_LIFE_MIN_DAYS,
    WEIGHT_MAX,
    WEIGHT_MIN,
    FairnessParams,
    weight_errors,
)

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

# Where a member proposal (estimate learning, task #15; weight change, task #16)
# is in its lifecycle. A decided proposal never changes again.
PROPOSAL_STATUS_PENDING = "pending"
PROPOSAL_STATUS_ACCEPTED = "accepted"
PROPOSAL_STATUS_DISMISSED = "dismissed"
ESTIMATE_PROPOSAL_STATUS_CHOICES = [
    (PROPOSAL_STATUS_PENDING, "Pending"),
    (PROPOSAL_STATUS_ACCEPTED, "Accepted"),
    (PROPOSAL_STATUS_DISMISSED, "Dismissed"),
]

# A fairness-weight change proposal (task #16) needs both members' approval
# before it is applied, so it has its own small lifecycle.
WEIGHT_PROPOSAL_STATUS_OPEN = "open"
WEIGHT_PROPOSAL_STATUS_APPLIED = "applied"
WEIGHT_PROPOSAL_STATUS_REJECTED = "rejected"
WEIGHT_PROPOSAL_STATUS_CHOICES = [
    (WEIGHT_PROPOSAL_STATUS_OPEN, "Open"),
    (WEIGHT_PROPOSAL_STATUS_APPLIED, "Applied"),
    (WEIGHT_PROPOSAL_STATUS_REJECTED, "Rejected"),
]

# An AI setup draft (task #18) is generated, then reviewed and applied (task
# #19). It is never partially applied.
AI_DRAFT_STATUS_DRAFT = "draft"
AI_DRAFT_STATUS_APPLIED = "applied"
AI_DRAFT_STATUS_CHOICES = [
    (AI_DRAFT_STATUS_DRAFT, "Draft"),
    (AI_DRAFT_STATUS_APPLIED, "Applied"),
]

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


class WeightValues(models.Model):
    """The three fairness-weight numbers, shared by the stored settings and by
    the change proposals (task #16) so the two can never drift apart.

    Defaults, meanings, and allowed ranges live in ``chores/fairness/weights.py``.
    """

    time_weight = models.FloatField(
        default=DEFAULT_TIME_WEIGHT,
        validators=[MinValueValidator(WEIGHT_MIN)],
        help_text="Multiplies a chore's estimated minutes.",
    )
    difficulty_weight = models.FloatField(
        default=DEFAULT_DIFFICULTY_WEIGHT,
        validators=[MinValueValidator(WEIGHT_MIN)],
        help_text="How far difficulty swings a chore's workload.",
    )
    decay_half_life_days = models.PositiveIntegerField(
        default=DEFAULT_DECAY_HALF_LIFE_DAYS,
        validators=[MinValueValidator(HALF_LIFE_MIN_DAYS)],
        help_text="Days after which a past contribution counts for half.",
    )

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        errors = weight_errors(
            self.time_weight, self.difficulty_weight, self.decay_half_life_days
        )
        if errors:
            raise ValidationError(errors)


class FairnessWeights(WeightValues):
    """A household's single row of fairness weights.

    Created with documented defaults whenever a ``Household`` is created (a
    ``post_save`` signal, see ``chores/signals.py``) and backfilled for any
    household that predates this model. Either member edits the values through
    ``/household/fairness/`` (task #16 later routes edits through approval).
    """

    household = models.OneToOneField(
        "Household",
        on_delete=models.CASCADE,
        related_name="fairness_weights",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "fairness weights"

    def __str__(self):
        return f"Fairness weights for {self.household}"

    def as_params(self):
        """This row as a framework-agnostic :class:`FairnessParams`."""
        return FairnessParams(
            time_weight=self.time_weight,
            difficulty_weight=self.difficulty_weight,
            decay_half_life_days=self.decay_half_life_days,
        )


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
    claimed_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claimed_occurrences",
        help_text=(
            "The member who volunteered to do this occurrence. Advisory only - "
            "it never changes the chore's primary owner."
        ),
    )
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

    def clean(self):
        super().clean()
        if (
            self.claimed_by_id is not None
            and self.chore_id is not None
            and self.claimed_by.household_id != self.chore.household_id
        ):
            raise ValidationError(
                {
                    "claimed_by": (
                        "The member claiming this occurrence must belong to "
                        "the chore's household."
                    )
                }
            )

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


class ContributionCredit(models.Model):
    """Records that a helper covered a chore occurrence owned by someone else.

    Written once, at completion time, when the completing member is not the
    chore's ``primary_owner`` and the chore has an owner at all. ``workload_value``
    is frozen from the chore's own estimate (not the ``Completion``'s optional
    actuals) via :func:`chores.fairness.workload_value` and never recomputed here
    - task #12 owns any reweighting. The occurrence is reachable as
    ``credit.completion.occurrence``; there is no separate occurrence FK.

    Both FKs use ``on_delete=PROTECT``: a membership with credit history can't be
    deleted out from under it.
    """

    completion = models.OneToOneField(
        Completion,
        on_delete=models.CASCADE,
        related_name="credit",
    )
    helper = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="credits_as_helper",
    )
    owner = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="credits_as_owner",
    )
    workload_value = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(helper=F("owner")),
                name="contributioncredit_helper_ne_owner",
            ),
        ]

    def __str__(self):
        return (
            f"{self.helper.user} covered {self.owner.user}'s "
            f"{self.completion.occurrence}"
        )

    def clean(self):
        super().clean()
        if (
            self.helper_id is not None
            and self.owner_id is not None
            and self.helper_id == self.owner_id
        ):
            raise ValidationError(
                "A contribution credit's helper and owner must be different "
                "members."
            )
        if (
            self.helper_id is not None
            and self.owner_id is not None
            and self.helper.household_id != self.owner.household_id
        ):
            raise ValidationError(
                "A contribution credit's helper and owner must belong to the "
                "same household."
            )


class EstimateProposal(models.Model):
    """A suggested change to a chore's time estimate, learned from history.

    Created ``pending`` by :func:`chores.proposals.generate_estimate_proposals`
    (which routes the comparison through
    :func:`chores.fairness.propose_estimate`). Either member can accept one on
    their own - the plan allows estimate changes to be accepted individually -
    or dismiss it. A decided proposal is frozen.
    """

    chore = models.ForeignKey(
        Chore,
        on_delete=models.CASCADE,
        related_name="estimate_proposals",
    )
    proposed_minutes = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    proposed_difficulty = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=DIFFICULTY_CHOICES,
    )
    rationale = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=ESTIMATE_PROPOSAL_STATUS_CHOICES,
        default=PROPOSAL_STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="estimate_decisions",
    )

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["chore"],
                condition=Q(status=PROPOSAL_STATUS_PENDING),
                name="one_pending_estimate_proposal_per_chore",
            ),
        ]

    def __str__(self):
        return (
            f"Estimate {self.proposed_minutes} min for {self.chore} "
            f"({self.status})"
        )

    @property
    def is_pending(self):
        return self.status == PROPOSAL_STATUS_PENDING


class WeightProposal(WeightValues):
    """Proposed fairness weights plus each member's approval.

    The values are copied onto the household's ``FairnessWeights`` only once
    both members approve (:meth:`apply`, one atomic block). Either member
    rejecting closes it with the weights untouched. At most one ``open``
    proposal per household (a partial unique constraint).
    """

    household = models.ForeignKey(
        "Household",
        on_delete=models.CASCADE,
        related_name="weight_proposals",
    )
    created_by = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="weight_proposals_created",
    )
    approved_by = models.ManyToManyField(
        Membership,
        related_name="weight_proposals_approved",
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=WEIGHT_PROPOSAL_STATUS_CHOICES,
        default=WEIGHT_PROPOSAL_STATUS_OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["household"],
                condition=Q(status=WEIGHT_PROPOSAL_STATUS_OPEN),
                name="one_open_weight_proposal_per_household",
            ),
        ]

    def __str__(self):
        return f"Weight proposal for {self.household} ({self.status})"

    @property
    def is_open(self):
        return self.status == WEIGHT_PROPOSAL_STATUS_OPEN

    def is_fully_approved(self):
        """True once every current household member has approved."""
        member_ids = set(
            self.household.memberships.values_list("id", flat=True)
        )
        approved_ids = set(self.approved_by.values_list("id", flat=True))
        return bool(member_ids) and member_ids <= approved_ids

    def apply(self):
        """Write the proposed values onto the household and close as applied."""
        from django.db import transaction

        with transaction.atomic():
            weights, _ = FairnessWeights.objects.get_or_create(
                household=self.household
            )
            weights.time_weight = self.time_weight
            weights.difficulty_weight = self.difficulty_weight
            weights.decay_half_life_days = self.decay_half_life_days
            weights.full_clean()
            weights.save()
            self.status = WEIGHT_PROPOSAL_STATUS_APPLIED
            self.resolved_at = timezone.now()
            self.save(update_fields=["status", "resolved_at"])

    def reject(self):
        self.status = WEIGHT_PROPOSAL_STATUS_REJECTED
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_at"])


class AISetupDraft(models.Model):
    """A validated, not-yet-applied chore plan from the Anthropic API (task #18).

    ``raw_response`` keeps the exact structured payload; ``chores`` /
    ``constraints`` / ``assignments`` hold the editable working copy that task
    #19's review screen mutates before it is applied.
    """

    household = models.ForeignKey(
        "Household",
        on_delete=models.CASCADE,
        related_name="ai_setup_drafts",
    )
    raw_response = models.JSONField()
    chores = models.JSONField(default=list, blank=True)
    constraints = models.JSONField(default=list, blank=True)
    assignments = models.JSONField(default=list, blank=True)
    reasoning = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=AI_DRAFT_STATUS_CHOICES,
        default=AI_DRAFT_STATUS_DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self):
        return f"AI setup draft for {self.household} ({self.status})"

    @property
    def is_draft(self):
        return self.status == AI_DRAFT_STATUS_DRAFT
