"""Views for Time Tracking, Timers, Manual Logging, and Timesheet Approvals."""

from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.translation import gettext_lazy as _
from apps.organizations.mixins import TenantRequiredMixin
from apps.organizations.models import OrganizationMembership
from apps.time_tracking.models import TimeEntry, ActiveTimer, Timesheet
from apps.time_tracking.forms import ManualTimeEntryForm, ActiveTimerStartForm, TimesheetReviewForm
from apps.time_tracking.services import (
    start_timer,
    stop_timer,
    log_manual_time,
    generate_timesheet,
    submit_timesheet,
    approve_timesheet,
    reject_timesheet,
)


class TimeTrackingDashboardView(TenantRequiredMixin, View):
    """Main dashboard displaying active timer, weekly summary, and recent logs."""

    def get(self, request):
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())

        active_timer = ActiveTimer.objects.filter(organization=request.tenant, user=request.user).first()

        recent_entries = (
            TimeEntry.objects.filter(organization=request.tenant, user=request.user)
            .select_related("project", "task")
            .order_by("-date", "-created_at")[:20]
        )

        today_sec = (
            TimeEntry.objects.filter(organization=request.tenant, user=request.user, date=today)
            .aggregate(s=Sum("duration_seconds"))["s"] or 0
        )
        week_sec = (
            TimeEntry.objects.filter(organization=request.tenant, user=request.user, date__gte=week_start)
            .aggregate(s=Sum("duration_seconds"))["s"] or 0
        )
        billable_sec = (
            TimeEntry.objects.filter(organization=request.tenant, user=request.user, is_billable=True)
            .aggregate(s=Sum("duration_seconds"))["s"] or 0
        )

        timer_form = ActiveTimerStartForm(organization=request.tenant)

        return render(
            request,
            "time_tracking/dashboard.html",
            {
                "active_timer": active_timer,
                "recent_entries": recent_entries,
                "today_hours": round(today_sec / 3600.0, 2),
                "week_hours": round(week_sec / 3600.0, 2),
                "billable_hours": round(billable_sec / 3600.0, 2),
                "timer_form": timer_form,
            },
        )


class TimerStartView(TenantRequiredMixin, View):
    """Start the active timer for the current user."""

    def post(self, request):
        form = ActiveTimerStartForm(request.tenant, request.POST)
        if form.is_valid():
            try:
                start_timer(
                    user=request.user,
                    organization=request.tenant,
                    project=form.cleaned_data["project"],
                    task=form.cleaned_data.get("task"),
                    description=form.cleaned_data.get("description", ""),
                    is_billable=form.cleaned_data.get("is_billable", True),
                )
                messages.success(request, _("Timer started."))
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, "message") else e))
        else:
            messages.error(request, _("Please select a project to start the timer."))
        return redirect("time_dashboard")


class TimerStopView(TenantRequiredMixin, View):
    """Stop the active timer and create a TimeEntry record."""

    def post(self, request):
        try:
            entry = stop_timer(user=request.user, organization=request.tenant)
            messages.success(request, _(f"Timer stopped. Logged {entry.hours}h."))
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))
        return redirect("time_dashboard")


class ManualTimeLogView(TenantRequiredMixin, View):
    """Form to manually record work hours."""

    def get(self, request):
        form = ManualTimeEntryForm(organization=request.tenant)
        return render(request, "time_tracking/manual_log.html", {"form": form})

    def post(self, request):
        form = ManualTimeEntryForm(request.tenant, request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.organization = request.tenant
            entry.user = request.user
            hours = form.cleaned_data["hours"]
            entry.duration_seconds = int(float(hours) * 3600)
            if not entry.start_time:
                date = form.cleaned_data["date"]
                entry.start_time = timezone.datetime.combine(date, timezone.datetime.min.time(), tzinfo=timezone.get_current_timezone())
            entry.save()
            messages.success(request, _(f"Successfully logged {entry.hours}h on {entry.project.key}."))
            return redirect("time_dashboard")
        return render(request, "time_tracking/manual_log.html", {"form": form})


class TimeEntryDeleteView(TenantRequiredMixin, View):
    """Delete a logged time entry."""

    def post(self, request, entry_id):
        entry = get_object_or_404(TimeEntry, id=entry_id, organization=request.tenant)
        is_admin = OrganizationMembership.objects.filter(
            organization=request.tenant,
            user=request.user,
            role__in=["owner", "admin"],
            is_active=True,
        ).exists()

        if entry.user != request.user and not is_admin:
            messages.error(request, _("You cannot delete someone else's time entry."))
            return redirect("time_dashboard")

        entry.delete()
        messages.info(request, _("Time entry deleted."))
        return redirect("time_dashboard")


class TimesheetListView(TenantRequiredMixin, View):
    """List timesheets with tabs for user timesheets and manager approval queue."""

    def get(self, request):
        tab = request.GET.get("tab", "my")

        my_timesheets = (
            Timesheet.objects.filter(organization=request.tenant, user=request.user)
            .order_by("-start_date")
        )

        is_manager = OrganizationMembership.objects.filter(
            organization=request.tenant,
            user=request.user,
            role__in=["owner", "admin", "manager"],
            is_active=True,
        ).exists()

        review_queue = []
        if is_manager:
            review_queue = (
                Timesheet.objects.filter(organization=request.tenant, status="submitted")
                .select_related("user")
                .order_by("-submitted_at")
            )

        if tab == "review" and is_manager:
            displayed = review_queue
        else:
            displayed = my_timesheets

        return render(
            request,
            "time_tracking/timesheet_list.html",
            {
                "timesheets": displayed,
                "current_tab": tab,
                "is_manager": is_manager,
                "review_count": len(review_queue) if is_manager else 0,
                "my_count": my_timesheets.count(),
            },
        )


class TimesheetDetailView(TenantRequiredMixin, View):
    """View detailed entries for a timesheet, with review form for managers."""

    def get(self, request, timesheet_id):
        timesheet = get_object_or_404(
            Timesheet.objects.select_related("user", "approved_by"),
            id=timesheet_id,
            organization=request.tenant,
        )

        entries = (
            TimeEntry.objects.filter(
                organization=request.tenant,
                user=timesheet.user,
                date__gte=timesheet.start_date,
                date__lte=timesheet.end_date,
            )
            .select_related("project", "task")
            .order_by("date", "start_time")
        )

        is_manager = OrganizationMembership.objects.filter(
            organization=request.tenant,
            user=request.user,
            role__in=["owner", "admin", "manager"],
            is_active=True,
        ).exists()

        can_review = is_manager and timesheet.status == "submitted" and timesheet.user != request.user
        review_form = TimesheetReviewForm() if can_review else None

        return render(
            request,
            "time_tracking/timesheet_detail.html",
            {
                "timesheet": timesheet,
                "entries": entries,
                "can_review": can_review,
                "review_form": review_form,
            },
        )


class TimesheetGenerateView(TenantRequiredMixin, View):
    """Generate or refresh current week or month timesheet for user."""

    def post(self, request):
        today = timezone.localdate()
        period_type = request.POST.get("period_type", "weekly")

        if period_type == "monthly":
            start_date = today.replace(day=1)
            # Last day of month
            next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_date = next_month - timedelta(days=1)
        else:
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)

        timesheet = generate_timesheet(
            user=request.user,
            organization=request.tenant,
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
        )
        messages.success(request, _(f"Generated {period_type} timesheet ({start_date} to {end_date}). Total: {timesheet.total_hours}h."))
        return redirect("timesheet_detail", timesheet_id=timesheet.id)


class TimesheetSubmitView(TenantRequiredMixin, View):
    """Submit a draft timesheet for manager review."""

    def post(self, request, timesheet_id):
        timesheet = get_object_or_404(Timesheet, id=timesheet_id, organization=request.tenant, user=request.user)
        try:
            submit_timesheet(timesheet)
            messages.success(request, _("Timesheet submitted for review."))
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))
        return redirect("timesheet_detail", timesheet_id=timesheet.id)


class TimesheetReviewView(TenantRequiredMixin, View):
    """Approve or reject a submitted employee timesheet."""

    def post(self, request, timesheet_id):
        timesheet = get_object_or_404(Timesheet, id=timesheet_id, organization=request.tenant)

        is_manager = OrganizationMembership.objects.filter(
            organization=request.tenant,
            user=request.user,
            role__in=["owner", "admin", "manager"],
            is_active=True,
        ).exists()

        if not is_manager:
            raise PermissionDenied("Only workspace managers can review timesheets.")

        form = TimesheetReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]
            notes = form.cleaned_data.get("notes", "")

            try:
                if action == "approved":
                    approve_timesheet(timesheet, approver=request.user, notes=notes)
                    messages.success(request, _(f"Timesheet for {timesheet.user.email} approved."))
                else:
                    reject_timesheet(timesheet, approver=request.user, reason=notes)
                    messages.info(request, _(f"Timesheet for {timesheet.user.email} rejected."))
            except ValidationError as e:
                messages.error(request, str(e))
        return redirect("timesheet_detail", timesheet_id=timesheet.id)

