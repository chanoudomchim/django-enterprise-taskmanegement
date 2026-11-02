"""AI Project Assistant models: Provider Config, Generation Requests, and Usage Audit."""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import TenantModel


class AIProviderConfiguration(TenantModel):
    """Organization-level AI provider toggle and model preferences."""

    PROVIDER_CHOICES = [
        ("mock", "Mock Engine (Deterministic)"),
        ("gemini", "Google Gemini API"),
        ("openai", "OpenAI API"),
    ]

    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, default="mock")
    model_name = models.CharField(max_length=100, default="gemini-1.5-flash")
    is_enabled = models.BooleanField(
        default=True,
        help_text=_("Allow users in this organization to invoke AI project assistance"),
    )
    api_key_env_var = models.CharField(
        max_length=100,
        default="GEMINI_API_KEY",
        help_text=_("Name of host environment variable storing provider API key"),
    )
    rate_limit_per_hour = models.PositiveIntegerField(default=60)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("AI provider configuration")
        verbose_name_plural = _("AI provider configurations")

    def __str__(self):
        status = "Enabled" if self.is_enabled else "Disabled"
        return f"{self.organization.name} - AI [{self.provider}] ({status})"


class AIGenerationRequest(TenantModel):
    """Asynchronous and synchronous AI job execution records."""

    FEATURE_CHOICES = [
        ("generate_tasks", "Generate Tasks from Description"),
        ("generate_subtasks", "Generate Subtasks"),
        ("summarize_progress", "Summarize Progress"),
        ("summarize_discussion", "Summarize Discussion"),
        ("risk_assessment", "Project Risk Assessment"),
        ("qa_assistant", "Project Q&A Assistant"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_requests",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_requests",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_requests",
    )
    feature = models.CharField(max_length=50, choices=FEATURE_CHOICES)
    prompt = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    response_text = models.TextField(blank=True)
    structured_output = models.JSONField(default=dict, blank=True)
    applied = models.BooleanField(
        default=False,
        help_text=_("Whether the generated suggestions were approved and committed to the database"),
    )
    tokens_used = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("AI generation request")
        verbose_name_plural = _("AI generation requests")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"AI [{self.feature}] for {self.user.email} [{self.status}]"


class AIUsageRecord(TenantModel):
    """Tracks token consumption and estimated AI costs per organization."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_usage_records",
    )
    feature = models.CharField(max_length=50)
    tokens_used = models.PositiveIntegerField(default=0)
    cost_estimate = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("AI usage record")
        verbose_name_plural = _("AI usage records")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.feature} ({self.tokens_used} tokens)"
