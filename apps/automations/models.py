"""Automation rules, trigger conditions, actions, and execution logs."""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import TenantModel


class AutomationRule(TenantModel):
    """User-defined automation workflow rule."""

    TRIGGER_CHOICES = [
        ("task_created", "When a Task is Created"),
        ("task_status_changed", "When Task Status Changes"),
        ("task_assigned", "When Task is Assigned"),
    ]

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    trigger = models.CharField(max_length=50, choices=TRIGGER_CHOICES)
    conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Filter criteria required to fire actions (e.g. {'status': 'completed'})"),
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="automation_rules",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("automation rule")
        verbose_name_plural = _("automation rules")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_trigger_display()})"


class AutomationAction(TenantModel):
    """Action to execute when parent rule criteria are met."""

    ACTION_CHOICES = [
        ("change_status", "Change Task Status"),
        ("send_notification", "Send Notification"),
        ("trigger_webhook", "Dispatch Outgoing Webhook"),
    ]

    rule = models.ForeignKey(
        AutomationRule,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES)
    parameters = models.JSONField(
        default=dict,
        help_text=_("Execution parameters (e.g. {'new_status': 'in_review'})"),
    )
    order = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = _("automation action")
        verbose_name_plural = _("automation actions")
        ordering = ["order"]

    def __str__(self):
        return f"Step {self.order}: {self.get_action_type_display()} on {self.rule.name}"


class AutomationExecution(TenantModel):
    """Audit log of triggered automation runs."""

    rule = models.ForeignKey(
        AutomationRule,
        on_delete=models.CASCADE,
        related_name="executions",
    )
    status = models.CharField(
        max_length=20,
        choices=[("success", "Success"), ("failed", "Failed")],
    )
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("automation execution")
        verbose_name_plural = _("automation executions")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.rule.name} run at {self.created_at} [{self.status}]"
