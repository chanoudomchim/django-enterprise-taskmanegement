"""Signals for accounts app."""

from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import User, UserProfile


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Ensure a UserProfile always exists for each User."""
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, "profile"):
            instance.profile.save()

