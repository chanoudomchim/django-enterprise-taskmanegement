"""Account and Identity models for WorkFlow Enterprise."""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.accounts.managers import CustomUserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model using UUID primary key and email as primary login identifier.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)

    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Designates whether this user should be treated as active."),
    )
    is_verified = models.BooleanField(
        _("verified"),
        default=False,
        help_text=_("Designates whether this user has verified their email."),
    )
    is_demo = models.BooleanField(
        _("demo record"),
        default=False,
        db_index=True,
        help_text=_("Marks demo data generated for seeding and testing."),
    )

    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    last_login = models.DateTimeField(_("last login"), blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    @property
    def short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.email.split("@")[0]


class UserProfile(models.Model):
    """Extended profile information for a User."""

    THEME_CHOICES = [
        ("light", "Light"),
        ("dark", "Dark"),
        ("system", "System Default"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", blank=True, null=True)
    phone_number = models.CharField(max_length=32, blank=True)
    title = models.CharField(max_length=100, blank=True, help_text=_("Job title or designation"))
    bio = models.TextField(blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    theme_preference = models.CharField(max_length=16, choices=THEME_CHOICES, default="light")
    language = models.CharField(max_length=8, default="en")
    is_telegram_connected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")

    def __str__(self):
        return f"Profile of {self.user.email}"


class UserSession(models.Model):
    """Track active user sessions for security and audit."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    session_key = models.CharField(max_length=40, db_index=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    last_activity = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("user session")
        verbose_name_plural = _("user sessions")
        ordering = ["-last_activity"]

    def __str__(self):
        return f"{self.user.email} - {self.ip_address}"


class EmailVerification(models.Model):
    """Email verification token lifecycle."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_verifications")
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("email verification")
        verbose_name_plural = _("email verifications")

    def __str__(self):
        return f"Verification for {self.user.email}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

