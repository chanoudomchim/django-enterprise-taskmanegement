"""Organization and Multi-Tenancy models for WorkFlow Enterprise."""

import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TenantQuerySet(models.QuerySet):
    """QuerySet for tenant-scoped models."""

    def for_tenant(self, organization):
        if organization is None:
            return self.none()
        return self.filter(organization=organization)


class TenantManager(models.Manager):
    """Manager for tenant-scoped models."""

    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_tenant(self, organization):
        return self.get_queryset().for_tenant(organization)


class TenantModel(models.Model):
    """
    Abstract base model that enforces organization-scoping on all tenant data.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        abstract = True


class Organization(models.Model):
    """Tenant organization entity."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    logo = models.ImageField(upload_to="org_logos/%Y/%m/", blank=True, null=True)
    primary_color = models.CharField(max_length=16, default="#0d6efd")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active")
    is_active = models.BooleanField(default=True, db_index=True)
    is_demo = models.BooleanField(default=False, db_index=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_organizations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "org"
            unique_slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)


class OrganizationMembership(models.Model):
    """Membership connecting Users to Organizations with specific roles."""

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Administrator"),
        ("manager", "Manager"),
        ("member", "Member"),
        ("guest", "Guest"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
        db_index=True,
    )
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default="member")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _("organization membership")
        verbose_name_plural = _("organization memberships")
        unique_together = [("organization", "user")]
        ordering = ["-joined_at"]

    def __str__(self):
        return f"{self.user.email} in {self.organization.name} ({self.role})"


class OrganizationInvitation(models.Model):
    """Invitation for users to join an organization."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("expired", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations",
        db_index=True,
    )
    email = models.EmailField(db_index=True)
    role = models.CharField(max_length=32, choices=OrganizationMembership.ROLE_CHOICES, default="member")
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_invitations",
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("organization invitation")
        verbose_name_plural = _("organization invitations")
        unique_together = [("organization", "email", "status")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invite for {self.email} to {self.organization.name}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at or self.status == "expired"


class OrganizationSettings(models.Model):
    """Settings and feature toggles for an Organization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="settings",
    )
    allow_member_invites = models.BooleanField(default=False)
    default_role = models.CharField(
        max_length=32,
        choices=OrganizationMembership.ROLE_CHOICES,
        default="member",
    )
    timezone = models.CharField(max_length=64, default="UTC")
    default_language = models.CharField(max_length=8, default="en")
    time_tracking_enabled = models.BooleanField(default=True)
    ai_assistant_enabled = models.BooleanField(default=True)
    telegram_notifications_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("organization settings")
        verbose_name_plural = _("organization settings")

    def __str__(self):
        return f"Settings for {self.organization.name}"


class SubscriptionPlan(models.Model):
    """Commercial subscription tiers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=50, unique=True)
    max_users = models.IntegerField(default=10)
    max_projects = models.IntegerField(default=20)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    billing_interval = models.CharField(max_length=16, default="monthly")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("subscription plan")
        verbose_name_plural = _("subscription plans")

    def __str__(self):
        return f"{self.name} (${self.price}/{self.billing_interval})"


class Subscription(models.Model):
    """Organization subscription instance."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("trial", "Trial"),
        ("past_due", "Past Due"),
        ("canceled", "Canceled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subscriptions",
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="trial")
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("subscription")
        verbose_name_plural = _("subscriptions")

    def __str__(self):
        return f"{self.organization.name} - {self.status}"
