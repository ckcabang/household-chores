"""Generate the missing chore occurrences across a forward date window.

The MVP runs this manually (see ``_docs/tech-stack-decision.md``); there is no
scheduler. Safe to run repeatedly - generation is idempotent.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from chores.models import Chore
from chores.occurrences import generate_occurrences


class Command(BaseCommand):
    help = "Generate missing chore occurrences for the next N days (default 30)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="How many days ahead to generate occurrences for (default 30).",
        )

    def handle(self, *args, **options):
        days = options["days"]
        through = timezone.localdate() + timedelta(days=days)

        created = 0
        with transaction.atomic():
            for chore in Chore.objects.all().iterator():
                created += len(generate_occurrences(chore, through))

        self.stdout.write(
            self.style.SUCCESS(f"Created {created} occurrence(s).")
        )
