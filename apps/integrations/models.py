"""API Clients, Webhooks, HMAC verification, and delivery records."""

import hmac
import hashlib
import json
import secrets
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import TenantModel


def generate_key():
    return secrets.token_hex(24)


def generate_secret():
    return secrets.token_hex(32)


class APIClient(TenantModel):
    """External API client credentials for REST API token authorization."""

    name = models.CharField(max_length=150)
    api_key = models.CharField(max_length=64, unique=True, db_index=True, default=generate_key)
    api_secret = models.CharField(max_length=128, default=generate_secret)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_clients",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("API client")
        verbose_name_plural = _("API clients")

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class WebhookEndpoint(TenantModel):
    """Subscribed outgoing webhook destinations."""

    url = models.URLField()
    secret = models.CharField(
        max_length=128,
        default=generate_secret,
        help_text=_("Shared secret for HMAC-SHA256 signature verification"),
    )
    events = models.JSONField(
        default=list,
        help_text=_("Subscribed event names (e.g. ['task.created', 'task.status_changed'])"),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("webhook endpoint")
        verbose_name_plural = _("webhook endpoints")

    def sign_payload(self, payload_dict):
        """Compute HMAC-SHA256 hex digest for JSON payload."""
        payload_bytes = json.dumps(payload_dict, sort_keys=True).encode("utf-8")
        return hmac.new(self.secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    def __str__(self):
        return f"{self.url} [{self.organization.name}]"


class WebhookDelivery(TenantModel):
    """Execution and delivery record for an outgoing webhook invocation."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    endpoint = models.ForeignKey(
        WebhookEndpoint,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    event = models.CharField(max_length=100)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    status_code = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    attempts = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("webhook delivery")
        verbose_name_plural = _("webhook deliveries")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Webhook {self.event} -> {self.endpoint.url} [{self.status}]"
