"""Signal handlers for campaigns app."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Campaign, CampaignMembership


@receiver(post_save, sender=Campaign)
def create_owner_membership(sender, instance, created, **kwargs):
    """Automatically create OWNER membership when a campaign is created."""
    if created:
        CampaignMembership.objects.create(
            campaign=instance, user=instance.owner, role="OWNER"
        )
