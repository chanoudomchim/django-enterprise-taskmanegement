"""Tasks domain models for WorkFlow Enterprise."""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.organizations.models import TenantModel


class TaskCategory(TenantModel):
    """Categorization for tasks (e.g., Bug, Feature, Improvement, Research)."""

    name = models.CharField(max_length=100)
    color = models.CharField(max_length=16, default="#6c757d")
    icon = models.CharField(max_length=64, default="bi-tag")

    class Meta:
        verbose_name = _("task category")
        verbose_name_plural = _("task categories")
        unique_together = [("organization", "name")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class TaskLabel(TenantModel):
    """Tags and labels for filtering tasks."""

    name = models.CharField(max_length=50)
    color = models.CharField(max_length=16, default="#0d6efd")

    class Meta:
        verbose_name = _("task label")
        verbose_name_plural = _("task labels")
        unique_together = [("organization", "name")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Task(TenantModel):
    """Central Task entity representing a unit of work."""

    STATUS_CHOICES = [
        ("backlog", "Backlog"),
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("in_review", "In Review"),
        ("blocked", "Blocked"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="tasks",
        db_index=True,
    )
    parent_task = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subtasks",
        db_index=True,
    )

    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    task_key = models.CharField(max_length=32, db_index=True)

    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="todo", db_index=True)
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default="medium", db_index=True)

    category = models.ForeignKey(
        TaskCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    labels = models.ManyToManyField(TaskLabel, blank=True, related_name="tasks")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_tasks",
    )

    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)

    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    progress = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    position = models.PositiveIntegerField(default=0, db_index=True)

    completed_date = models.DateTimeField(null=True, blank=True)
    is_demo = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = _("task")
        verbose_name_plural = _("tasks")
        unique_together = [("organization", "task_key")]
        ordering = ["position", "-created_at"]

    def __str__(self):
        return f"[{self.task_key}] {self.title}"

    def save(self, *args, **kwargs):
        # Auto-generate task key if not provided
        if not self.task_key:
            count = Task.objects.filter(project=self.project).count() + 1
            self.task_key = f"{self.project.key}-{count}"
        
        # Track completion status transition
        if self.status == "completed" and not self.completed_date:
            self.completed_date = timezone.now()
            self.progress = 100
        elif self.status != "completed" and self.completed_date:
            self.completed_date = None

        super().save(*args, **kwargs)

        # Trigger project progress update
        if self.project:
            self.project.update_progress()


class TaskAssignment(models.Model):
    """Assigning users to a task."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="assignments",
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_assignments",
        db_index=True,
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delegated_task_assignments",
    )

    class Meta:
        verbose_name = _("task assignment")
        verbose_name_plural = _("task assignments")
        unique_together = [("task", "user")]

    def __str__(self):
        return f"{self.user.email} -> {self.task.task_key}"


class TaskWatcher(models.Model):
    """Users monitoring task updates."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="watchers",
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="watched_tasks",
        db_index=True,
    )
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _("task watcher")
        verbose_name_plural = _("task watchers")
        unique_together = [("task", "user")]

    def __str__(self):
        return f"{self.user.email} watches {self.task.task_key}"


class TaskChecklist(models.Model):
    """Checklist group on a task."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="checklists",
        db_index=True,
    )
    title = models.CharField(max_length=150, default="Checklist")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("task checklist")
        verbose_name_plural = _("task checklists")
        ordering = ["position"]

    def __str__(self):
        return f"{self.title} on {self.task.task_key}"


class TaskChecklistItem(models.Model):
    """Individual item within a task checklist."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    checklist = models.ForeignKey(
        TaskChecklist,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    content = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_checklist_items",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("checklist item")
        verbose_name_plural = _("checklist items")
        ordering = ["position"]

    def __str__(self):
        return self.content


class TaskDependency(models.Model):
    """Task dependency relation (e.g., blocking, related)."""

    TYPE_CHOICES = [
        ("blocks", "Blocks"),
        ("relates_to", "Relates To"),
        ("duplicates", "Duplicates"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blocking_task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="blocks_tasks",
    )
    dependent_task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="blocked_by_tasks",
    )
    dependency_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="blocks")

    class Meta:
        verbose_name = _("task dependency")
        verbose_name_plural = _("task dependencies")
        unique_together = [("blocking_task", "dependent_task")]

    def __str__(self):
        return f"{self.blocking_task.task_key} {self.dependency_type} {self.dependent_task.task_key}"


class TaskRecurrence(models.Model):
    """Configuration for recurring tasks."""

    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.OneToOneField(
        Task,
        on_delete=models.CASCADE,
        related_name="recurrence",
    )
    frequency = models.CharField(max_length=16, choices=FREQUENCY_CHOICES, default="weekly")
    interval = models.PositiveIntegerField(default=1)
    next_due = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("task recurrence")
        verbose_name_plural = _("task recurrences")

    def __str__(self):
        return f"Every {self.interval} {self.frequency} for {self.task.task_key}"


class TaskCustomField(TenantModel):
    """Dynamic custom field definition for an organization."""

    FIELD_TYPES = [
        ("text", "Text"),
        ("number", "Number"),
        ("date", "Date"),
        ("select", "Dropdown"),
    ]

    name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=16, choices=FIELD_TYPES, default="text")
    is_required = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("task custom field")
        verbose_name_plural = _("task custom fields")
        unique_together = [("organization", "name")]

    def __str__(self):
        return f"{self.name} ({self.field_type})"


class TaskCustomFieldValue(models.Model):
    """Value assigned to a custom field on a task."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="custom_values",
    )
    field = models.ForeignKey(
        TaskCustomField,
        on_delete=models.CASCADE,
        related_name="values",
    )
    value = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = _("custom field value")
        verbose_name_plural = _("custom field values")
        unique_together = [("task", "field")]

    def __str__(self):
        return f"{self.task.task_key} -> {self.field.name}: {self.value}"
