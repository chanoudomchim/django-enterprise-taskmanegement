"""Notification and Telegram integration models for WorkFlow Enterprise."""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import TenantModel


class Notification(TenantModel):
    """User notification tracking in-app, email, and Telegram dispatches."""

    TYPE_CHOICES = [
        ("task_assigned", "Task Assigned"),
        ("task_due_reminder", "Task Due Reminder"),
        ("task_status_changed", "Task Status Changed"),
        ("comment_mention", "Mentioned in Comment"),
        ("approval_requested", "Approval Requested"),
        ("approval_decided", "Approval Decision"),
        ("timesheet_submitted", "Timesheet Submitted"),
        ("timesheet_decided", "Timesheet Decision"),
        ("system", "System Notice"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
    )
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default="system")
    title = models.CharField(max_length=200)
    body = models.TextField()
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    target_url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
            models.Index(fields=["organization", "-created_at"]),
        ]

    def mark_as_read(self):
        """Mark notification as read with timestamp."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    def __str__(self):
        return f"[{self.get_notification_type_display()}] to {self.recipient.email}: {self.title}"


class NotificationPreference(TenantModel):
    """User-configured notification channels and subscriptions per organization."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    email_notifications = models.BooleanField(default=True)
    telegram_notifications = models.BooleanField(default=False)
    in_app_notifications = models.BooleanField(default=True)
    notify_on_task_assigned = models.BooleanField(default=True)
    notify_on_comment_mention = models.BooleanField(default=True)
    notify_on_due_date = models.BooleanField(default=True)
    notify_on_approvals = models.BooleanField(default=True)
    daily_summary_enabled = models.BooleanField(default=False)
    weekly_summary_enabled = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("notification preference")
        verbose_name_plural = _("notification preferences")
        unique_together = [("organization", "user")]

    def __str__(self):
        return f"Notification Preferences for {self.user.email} in {self.organization.name}"


class NotificationDelivery(TenantModel):
    """Delivery attempt log across delivery channels (In-app, Email, Telegram)."""

    CHANNEL_CHOICES = [
        ("in_app", "In-App"),
        ("email", "Email"),
        ("telegram", "Telegram"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("notification delivery")
        verbose_name_plural = _("notification deliveries")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.channel} delivery for {self.notification_id} [{self.status}]"


class TelegramAccount(TenantModel):
    """Links a user to a Telegram chat ID with verification."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_account",
    )
    telegram_chat_id = models.CharField(max_length=64, blank=True)
    telegram_username = models.CharField(max_length=100, blank=True)
    verification_code = models.CharField(max_length=32, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("telegram account")
        verbose_name_plural = _("telegram accounts")

    def __str__(self):
        status = "Verified" if self.is_verified else "Pending"
        return f"{self.user.email} -> Telegram ({self.telegram_username or self.telegram_chat_id}) [{status}]"


class TelegramIntegration(TenantModel):
    """Organization-level Telegram bot settings."""

    bot_name = models.CharField(max_length=100, default="WorkFlowBot")
    bot_token = models.CharField(max_length=255, blank=True, help_text=_("Telegram Bot API token"))
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("telegram integration")
        verbose_name_plural = _("telegram integrations")

    def __str__(self):
        return f"Telegram Bot '{self.bot_name}' for {self.organization.name}"
