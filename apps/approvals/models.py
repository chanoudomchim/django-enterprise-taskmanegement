"""Approval Management models for WorkFlow Enterprise: Multi-stage workflows, requests, and decisions."""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import TenantModel


class ApprovalWorkflow(TenantModel):
    """Defines an organizational multi-step approval workflow template."""

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="approval_workflows",
        help_text=_("Optional project scope; if unset, workflow is organization-wide."),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("approval workflow")
        verbose_name_plural = _("approval workflows")
        ordering = ["name"]

    def __str__(self):
        return self.name


class ApprovalStage(TenantModel):
    """An individual sequential stage in an approval workflow."""

    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name="stages",
    )
    name = models.CharField(max_length=100)
    step_number = models.PositiveIntegerField(default=1)
    required_role = models.ForeignKey(
        "rbac.OrganizationRole",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_stages",
        help_text=_("Any user assigned to this role can review and decide this stage."),
    )
    assigned_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_approval_stages",
        help_text=_("Specific user assigned to approve this stage."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("approval stage")
        verbose_name_plural = _("approval stages")
        unique_together = [("workflow", "step_number")]
        ordering = ["step_number"]

    def clean(self):
        super().clean()
        if self.workflow and self.workflow.organization_id != self.organization_id:
            raise ValidationError(_("Workflow organization does not match stage organization."))
        if self.required_role and self.required_role.organization_id != self.organization_id:
            raise ValidationError(_("Required role belongs to a different organization."))

    def __str__(self):
        return f"{self.workflow.name} - Step {self.step_number}: {self.name}"


class ApprovalRequest(TenantModel):
    """An instance of a request undergoing workflow review."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name="requests",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="approval_requests",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="approval_requests",
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="approval_requests",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    current_stage = models.ForeignKey(
        ApprovalStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("approval request")
        verbose_name_plural = _("approval requests")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status", "-created_at"]),
            models.Index(fields=["requester", "status"]),
        ]

    def clean(self):
        super().clean()
        if self.task and self.task.organization_id != self.organization_id:
            raise ValidationError(_("Task organization mismatch."))
        if self.project and self.project.organization_id != self.organization_id:
            raise ValidationError(_("Project organization mismatch."))

    def can_user_decide(self, user):
        """Check if user is authorized to approve/reject the current stage."""
        if not user or not user.is_authenticated or self.status != "pending":
            return False

        if not self.current_stage:
            return False

        # If specific approver assigned:
        if self.current_stage.assigned_approver_id == user.id:
            return True

        # If required role specified:
        if self.current_stage.required_role:
            has_role = self.current_stage.required_role.user_assignments.filter(user=user).exists()
            if has_role:
                return True

        # Workspace owner or admin fallback
        from apps.organizations.models import OrganizationMembership
        membership = OrganizationMembership.objects.filter(
            organization_id=self.organization_id,
            user=user,
            is_active=True,
            role__in=["owner", "admin"],
        ).exists()
        return membership

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"


class ApprovalDecision(TenantModel):
    """A formal audit-logged decision recorded by an approver for a specific stage."""

    DECISION_CHOICES = [
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("changes_requested", "Changes Requested"),
    ]

    request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name="decisions",
    )
    stage = models.ForeignKey(
        ApprovalStage,
        on_delete=models.CASCADE,
        related_name="decisions",
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="approval_decisions",
    )
    decision = models.CharField(max_length=30, choices=DECISION_CHOICES)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("approval decision")
        verbose_name_plural = _("approval decisions")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.approver.email} - {self.decision} on {self.stage.name}"
