"""Scan completion history and create pending estimate-change proposals.

The MVP has no scheduler; run this by hand (or wire it to cron later). Safe to
run repeatedly - a chore that already has a pending proposal is skipped.
"""

from django.core.management.base import BaseCommand

from chores.models import Household
from chores.proposals import generate_estimate_proposals


class Command(BaseCommand):
    help = "Create pending estimate-change proposals from logged actual times."

    def handle(self, *args, **options):
        total = 0
        for household in Household.objects.all():
            total += len(generate_estimate_proposals(household))
        self.stdout.write(
            self.style.SUCCESS(f"Created {total} estimate proposal(s).")
        )
