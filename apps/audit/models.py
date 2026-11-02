"""Immutable security audit log model for WorkFlow Enterprise."""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import TenantModel


class AuditLog(TenantModel):
    """
    Immutable audit trail recording notable state mutations, access attempts,
    and administrative configuration updates with IP and user-agent metadata.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(
        max_length=50,
        help_text=_("Action performed (e.g. create, update, delete, export, login)"),
    )
    model_name = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=64, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Field-level deltas or metadata attributes"),
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("audit log")
        verbose_name_plural = _("audit logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["model_name", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        user_str = self.user.email if self.user else "System"
        return f"[{self.action.upper()}] {self.model_name}:{self.object_id} by {user_str} ({self.created_at})"
