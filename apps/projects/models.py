"""Projects domain models for WorkFlow Enterprise."""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import TenantModel


class Project(TenantModel):
    """Project entity belonging to an organization."""

    STATUS_CHOICES = [
        ("planning", "Planning"),
        ("active", "Active"),
        ("on_hold", "On Hold"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("archived", "Archived"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    name = models.CharField(max_length=200, db_index=True)
    key = models.CharField(max_length=16, db_index=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planning", db_index=True)
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default="medium")

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_projects",
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_projects",
    )

    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    spent_budget = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    progress_percentage = models.PositiveSmallIntegerField(default=0)

    start_date = models.DateField(null=True, blank=True)
    target_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)

    is_template = models.BooleanField(default=False)
    is_demo = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = _("project")
        verbose_name_plural = _("projects")
        unique_together = [("organization", "key")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.key}] {self.name}"

    def update_progress(self):
        """Calculate progress from completed tasks."""
        total_tasks = self.tasks.count()
        if total_tasks > 0:
            completed_tasks = self.tasks.filter(status="completed").count()
            self.progress_percentage = int((completed_tasks / total_tasks) * 100)
            self.save(update_fields=["progress_percentage"])


class ProjectMembership(models.Model):
    """User membership within a project."""

    ROLE_CHOICES = [
        ("manager", "Project Manager"),
        ("member", "Member"),
        ("viewer", "Viewer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships",
        db_index=True,
    )
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _("project membership")
        verbose_name_plural = _("project memberships")
        unique_together = [("project", "user")]

    def __str__(self):
        return f"{self.user.email} on {self.project.name} ({self.role})"


class ProjectTeam(models.Model):
    """Mapping a team to a project."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="assigned_teams",
        db_index=True,
    )
    team = models.ForeignKey(
        "departments.Team",
        on_delete=models.CASCADE,
        related_name="assigned_projects",
        db_index=True,
    )
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _("project team")
        verbose_name_plural = _("project teams")
        unique_together = [("project", "team")]

    def __str__(self):
        return f"Team {self.team.name} -> {self.project.name}"


class ProjectMilestone(models.Model):
    """Milestone checkpoint in a project."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="milestones",
        db_index=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("project milestone")
        verbose_name_plural = _("project milestones")
        ordering = ["order", "due_date"]

    def __str__(self):
        return f"{self.title} ({self.project.key})"


class ProjectTemplate(TenantModel):
    """Reusable template for recurring project structures."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    template_data = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = _("project template")
        verbose_name_plural = _("project templates")

    def __str__(self):
        return self.name
