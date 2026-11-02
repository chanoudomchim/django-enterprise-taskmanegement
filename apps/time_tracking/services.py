"""Services for Time Tracking: Timers, Manual Logging, Timesheets, and Manager Approvals."""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from apps.time_tracking.models import (
    TimeEntry,
    ActiveTimer,
    Timesheet,
    TimesheetEntry,
    TimesheetApproval,
)
from apps.collaboration.services import log_activity


@transaction.atomic
def start_timer(user, organization, project, task=None, description="", is_billable=True):
    """Start an active timer for the user. Enforces the single active timer rule."""
    existing = ActiveTimer.objects.filter(user=user).first()
    if existing:
        raise ValidationError("An active timer is already running. Please stop it before starting a new one.")

    timer = ActiveTimer.objects.create(
        organization=organization,
        user=user,
        project=project,
        task=task,
        description=description,
        is_billable=is_billable,
        started_at=timezone.now(),
    )
    return timer


@transaction.atomic
def stop_timer(user, organization):
    """Stop running timer and persist duration as a permanent TimeEntry."""
    timer = ActiveTimer.objects.filter(user=user, organization=organization).first()
    if not timer:
        raise ValidationError("No active timer found to stop.")

    now = timezone.now()
    duration_sec = max(1, int((now - timer.started_at).total_seconds()))

    entry = TimeEntry.objects.create(
        organization=organization,
        user=user,
        project=timer.project,
        task=timer.task,
        description=timer.description,
        start_time=timer.started_at,
        end_time=now,
        duration_seconds=duration_sec,
        is_billable=timer.is_billable,
        date=timer.started_at.date(),
    )

    timer.delete()

    log_activity(
        organization=organization,
        actor=user,
        action="created",
        description=f"Logged {entry.hours}h on [{timer.project.key}] via timer",
        task=timer.task,
        project=timer.project,
    )

    return entry


@transaction.atomic
def log_manual_time(user, organization, project, hours, date, task=None, description="", is_billable=True, hourly_rate=None):
    """Log work hours manually without a timer."""
    duration_seconds = int(float(hours) * 3600)
    now = timezone.now()
    start_time = timezone.datetime.combine(date, timezone.datetime.min.time(), tzinfo=timezone.get_current_timezone())
    end_time = start_time + timezone.timedelta(seconds=duration_seconds)

    entry = TimeEntry.objects.create(
        organization=organization,
        user=user,
        project=project,
        task=task,
        description=description,
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration_seconds,
        is_billable=is_billable,
        hourly_rate=hourly_rate,
        date=date,
    )

    log_activity(
        organization=organization,
        actor=user,
        action="created",
        description=f"Manually logged {entry.hours}h on [{project.key}]",
        task=task,
        project=project,
    )

    return entry


@transaction.atomic
def generate_timesheet(user, organization, start_date, end_date, period_type="weekly"):
    """Aggregate or initialize a user timesheet for a date range."""
    timesheet, created = Timesheet.objects.get_or_create(
        organization=organization,
        user=user,
        start_date=start_date,
        end_date=end_date,
        defaults={"period_type": period_type, "status": "draft"},
    )

    # Link all time entries in the date range
    entries = TimeEntry.objects.filter(
        organization=organization,
        user=user,
        date__gte=start_date,
        date__lte=end_date,
    )

    for entry in entries:
        TimesheetEntry.objects.get_or_create(
            organization=organization,
            timesheet=timesheet,
            time_entry=entry,
        )

    timesheet.recalculate_totals()
    return timesheet


@transaction.atomic
def submit_timesheet(timesheet):
    """Submit a draft timesheet for manager review."""
    if timesheet.status not in ["draft", "rejected"]:
        raise ValidationError("Only draft or rejected timesheets can be submitted.")

    timesheet.recalculate_totals()
    timesheet.status = "submitted"
    timesheet.submitted_at = timezone.now()
    timesheet.rejection_reason = ""
    timesheet.save(update_fields=["status", "submitted_at", "rejection_reason", "updated_at"])

    log_activity(
        organization=timesheet.organization,
        actor=timesheet.user,
        action="created",
        description=f"Submitted {timesheet.period_type} timesheet ({timesheet.start_date} to {timesheet.end_date}) with {timesheet.total_hours}h",
    )
    return timesheet


@transaction.atomic
def approve_timesheet(timesheet, approver, notes=""):
    """Manager approves a submitted timesheet."""
    if timesheet.status != "submitted":
        raise ValidationError("Only submitted timesheets can be approved.")

    timesheet.status = "approved"
    timesheet.approved_by = approver
    timesheet.approved_at = timezone.now()
    timesheet.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

    TimesheetApproval.objects.create(
        organization=timesheet.organization,
        timesheet=timesheet,
        approver=approver,
        action="approved",
        notes=notes,
    )

    log_activity(
        organization=timesheet.organization,
        actor=approver,
        action="approved",
        description=f"{approver.email} approved timesheet for {timesheet.user.email} ({timesheet.total_hours}h)",
    )
    return timesheet


@transaction.atomic
def reject_timesheet(timesheet, approver, reason=""):
    """Manager rejects a submitted timesheet with feedback."""
    if timesheet.status != "submitted":
        raise ValidationError("Only submitted timesheets can be rejected.")

    timesheet.status = "rejected"
    timesheet.rejection_reason = reason
    timesheet.save(update_fields=["status", "rejection_reason", "updated_at"])

    TimesheetApproval.objects.create(
        organization=timesheet.organization,
        timesheet=timesheet,
        approver=approver,
        action="rejected",
        notes=reason,
    )

    log_activity(
        organization=timesheet.organization,
        actor=approver,
        action="rejected",
        description=f"{approver.email} rejected timesheet for {timesheet.user.email}: {reason}",
    )
    return timesheet

