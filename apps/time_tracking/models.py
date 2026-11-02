"""Time Tracking models for WorkFlow Enterprise: Entries, Active Timers, Timesheets, and Approvals."""

import math
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import TenantModel


class TimeEntry(TenantModel):
    """Logged work session against a project and optional task."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="time_entries",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="time_entries",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="time_entries",
    )
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(
        default=0,
        help_text=_("Logged duration in seconds"),
    )
    is_billable = models.BooleanField(default=True)
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Billing rate per hour"),
    )
    date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("time entry")
        verbose_name_plural = _("time entries")
        ordering = ["-date", "-start_time"]
        indexes = [
            models.Index(fields=["organization", "-date"]),
            models.Index(fields=["user", "-date"]),
            models.Index(fields=["project", "-date"]),
            models.Index(fields=["task", "-date"]),
        ]

    def clean(self):
        super().clean()
        if self.organization_id and self.task and self.task.organization_id != self.organization_id:
            raise ValidationError(_("Task organization mismatch."))
        if self.organization_id and self.project and self.project.organization_id != self.organization_id:
            raise ValidationError(_("Project organization mismatch."))
        if self.end_time and self.start_time and self.end_time < self.start_time:
            raise ValidationError(_("End time cannot be earlier than start time."))

    @property
    def hours(self):
        """Duration converted to hours rounded to 2 decimal places."""
        return round(self.duration_seconds / 3600.0, 2)

    def save(self, *args, **kwargs):
        # Calculate duration if end_time is set
        if self.start_time and self.end_time and not self.duration_seconds:
            self.duration_seconds = int((self.end_time - self.start_time).total_seconds())
        if not self.date and self.start_time:
            self.date = self.start_time.date()
        super().save(*args, **kwargs)

        # Update task actual hours if task is attached
        if self.task_id:
            from django.db.models import Sum
            total_sec = TimeEntry.objects.filter(task_id=self.task_id).aggregate(s=Sum("duration_seconds"))["s"] or 0
            self.task.actual_hours = round(total_sec / 3600.0, 2)
            self.task.save(update_fields=["actual_hours", "updated_at"])

    def __str__(self):
        return f"{self.user.email} - {self.hours}h on {self.project.key} ({self.date})"


class ActiveTimer(TenantModel):
    """
    Enforces a strict single active timer constraint per user.
    Uses OneToOneField on the user within the organization.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="active_timer",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_timers",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="active_timers",
    )
    description = models.TextField(blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    is_billable = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("active timer")
        verbose_name_plural = _("active timers")

    def clean(self):
        super().clean()
        if self.task and self.task.organization_id != self.organization_id:
            raise ValidationError(_("Task organization mismatch."))
        if self.project and self.project.organization_id != self.organization_id:
            raise ValidationError(_("Project organization mismatch."))

    @property
    def elapsed_seconds(self):
        """Current elapsed seconds since timer started."""
        return max(0, int((timezone.now() - self.started_at).total_seconds()))

    def __str__(self):
        return f"Active timer for {self.user.email} on {self.project.key}"


class Timesheet(TenantModel):
    """Weekly or monthly aggregated timesheet for employee time tracking and manager approvals."""

    PERIOD_CHOICES = [
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="timesheets",
    )
    period_type = models.CharField(max_length=20, choices=PERIOD_CHOICES, default="weekly")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft")
    total_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    billable_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_timesheets",
    )
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("timesheet")
        verbose_name_plural = _("timesheets")
        unique_together = [("organization", "user", "start_date", "end_date")]
        ordering = ["-start_date"]

    def recalculate_totals(self):
        """Calculate total hours and billable hours from connected entries."""
        from django.db.models import Sum
        entries = TimeEntry.objects.filter(
            organization=self.organization,
            user=self.user,
            date__gte=self.start_date,
            date__lte=self.end_date,
        )
        total_sec = entries.aggregate(s=Sum("duration_seconds"))["s"] or 0
        billable_sec = entries.filter(is_billable=True).aggregate(s=Sum("duration_seconds"))["s"] or 0

        self.total_hours = round(total_sec / 3600.0, 2)
        self.billable_hours = round(billable_sec / 3600.0, 2)
        self.save(update_fields=["total_hours", "billable_hours", "updated_at"])

    def __str__(self):
        return f"Timesheet ({self.start_date} to {self.end_date}) - {self.user.email} [{self.status}]"


class TimesheetEntry(TenantModel):
    """Associates a specific TimeEntry to a Timesheet."""

    timesheet = models.ForeignKey(
        Timesheet,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    time_entry = models.OneToOneField(
        TimeEntry,
        on_delete=models.CASCADE,
        related_name="timesheet_entry",
    )

    class Meta:
        verbose_name = _("timesheet entry")
        verbose_name_plural = _("timesheet entries")

    def __str__(self):
        return f"{self.timesheet_id} -> {self.time_entry_id}"


class TimesheetApproval(TenantModel):
    """Audit log of manager decisions on timesheets."""

    timesheet = models.ForeignKey(
        Timesheet,
        on_delete=models.CASCADE,
        related_name="approvals",
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="timesheet_approvals",
    )
    action = models.CharField(max_length=20, choices=[("approved", "Approved"), ("rejected", "Rejected")])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("timesheet approval")
        verbose_name_plural = _("timesheet approvals")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.approver.email} {self.action} timesheet {self.timesheet_id}"
