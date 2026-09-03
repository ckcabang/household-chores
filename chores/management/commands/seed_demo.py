"""Build a complete demo household for local testing and screenshots.

Not production data. Refuses to run with ``DEBUG=False`` unless ``--force``.
Documented credentials (see the README):

    demo-alice / demo-pass-alice
    demo-bob   / demo-pass-bob
"""

from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from chores.models import (
    Chore,
    ChoreOccurrence,
    Completion,
    ContributionCredit,
    Household,
    Membership,
    OCCURRENCE_STATUS_ACTIVE,
    OCCURRENCE_STATUS_COMPLETED,
)
from chores.occurrences import generate_occurrences
from chores.fairness import workload_value

DEMO_HOUSEHOLD_NAME = "Demo Household"
DEMO_USERS = [
    ("demo-alice", "demo-pass-alice"),
    ("demo-bob", "demo-pass-bob"),
]

# (name, cadence_days, estimated_minutes, difficulty)
DEMO_CHORES = [
    ("Wash the dishes", 1, 15, 2),
    ("Take out the rubbish", 3, 5, 1),
    ("Vacuum the flat", 7, 30, 3),
    ("Clean the bathroom", 7, 40, 4),
    ("Do the laundry", 4, 25, 2),
    ("Deep-clean the kitchen", 30, 90, 5),
]


class Command(BaseCommand):
    help = "Create a demo household with chores, occurrences, and history."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete any existing demo data first.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run even when DEBUG is False.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "Refusing to seed demo data with DEBUG=False. Pass --force to "
                "override."
            )

        User = get_user_model()
        existing = Household.objects.filter(name=DEMO_HOUSEHOLD_NAME)

        if existing.exists():
            if not options["reset"]:
                raise CommandError(
                    "Demo data already exists. Re-run with --reset to rebuild "
                    "it."
                )
            self._reset(User, existing)

        with transaction.atomic():
            counts = self._build(User)

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded demo household: "
                f"{counts['chores']} chores, "
                f"{counts['occurrences']} occurrences, "
                f"{counts['completions']} completions, "
                f"{counts['credits']} contribution credit(s)."
            )
        )
        self.stdout.write("Log in as demo-alice / demo-pass-alice.")

    def _reset(self, User, households):
        household_ids = list(households.values_list("id", flat=True))
        # Completion.completed_by and ContributionCredit.helper/owner PROTECT
        # their Membership, so clear those before the household cascade.
        ContributionCredit.objects.filter(
            helper__household_id__in=household_ids
        ).delete()
        Completion.objects.filter(
            completed_by__household_id__in=household_ids
        ).delete()
        # The cascade now reaches memberships, chores, occurrences, proposals
        # and drafts.
        households.delete()
        User.objects.filter(
            username__in=[u for u, _ in DEMO_USERS]
        ).delete()

    def _build(self, User):
        household = Household.objects.create(name=DEMO_HOUSEHOLD_NAME)
        memberships = []
        for username, password in DEMO_USERS:
            user = User.objects.create_user(username=username, password=password)
            memberships.append(
                Membership.objects.create(user=user, household=household)
            )
        alice, bob = memberships

        today = timezone.localdate()
        # Anchor chores 45 days ago so generate_occurrences produces history.
        created_at = timezone.now() - timedelta(days=45)
        chores = []
        for i, (name, cadence, minutes, difficulty) in enumerate(DEMO_CHORES):
            owner = alice if i % 2 == 0 else bob
            chore = Chore.objects.create(
                household=household,
                name=name,
                cadence_days=cadence,
                estimated_minutes=minutes,
                difficulty=difficulty,
                primary_owner=owner,
            )
            Chore.objects.filter(pk=chore.pk).update(created_at=created_at)
            chore.refresh_from_db()
            chores.append(chore)

        occurrences = 0
        for chore in chores:
            occurrences += len(
                generate_occurrences(chore, today + timedelta(days=14))
            )

        completions = 0
        credits = 0
        past = ChoreOccurrence.objects.filter(
            chore__household=household,
            status=OCCURRENCE_STATUS_ACTIVE,
            due_date__lt=today,
        ).select_related("chore", "chore__primary_owner")

        for n, occ in enumerate(past):
            # The owner usually does their own chore; every 4th is covered by
            # the other member so there is at least one contribution credit.
            owner = occ.chore.primary_owner
            other = bob if owner == alice else alice
            actor = other if n % 4 == 3 else owner

            occ.status = OCCURRENCE_STATUS_COMPLETED
            occ.completed_at = timezone.make_aware(
                datetime.combine(occ.due_date, time(12, 0))
            )
            occ.save(update_fields=["status", "completed_at"])
            completion = Completion.objects.create(
                occurrence=occ,
                completed_by=actor,
                actual_minutes=occ.chore.estimated_minutes,
            )
            completions += 1

            if actor != owner:
                ContributionCredit.objects.create(
                    completion=completion,
                    helper=actor,
                    owner=owner,
                    workload_value=workload_value(
                        occ.chore.estimated_minutes, occ.chore.difficulty
                    ),
                )
                credits += 1

        return {
            "chores": len(chores),
            "occurrences": occurrences,
            "completions": completions,
            "credits": credits,
        }
