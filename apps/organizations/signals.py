"""Signals for organizations app."""

from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.organizations.models import Organization, OrganizationSettings


@receiver(post_save, sender=Organization)
def create_organization_settings(sender, instance, created, **kwargs):
    """Auto-provision default organization settings and RBAC roles upon creation."""
    if created:
        if not hasattr(instance, "settings"):
            OrganizationSettings.objects.create(organization=instance)
        from apps.rbac.services import seed_default_organization_roles
        seed_default_organization_roles(instance)

