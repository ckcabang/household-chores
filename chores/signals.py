"""App signal handlers, wired up in ``ChoresConfig.ready``."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import FairnessWeights, Household


@receiver(post_save, sender=Household)
def create_fairness_weights(sender, instance, created, **kwargs):
    """Give every household exactly one ``FairnessWeights`` row with defaults.

    Runs for the create view, the admin, the shell, and tests alike.
    ``get_or_create`` keeps it a no-op for a household that already has one.
    """
    if created:
        FairnessWeights.objects.get_or_create(household=instance)
