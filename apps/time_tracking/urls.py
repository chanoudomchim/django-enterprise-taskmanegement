"""URL patterns for Time Tracking and Timesheets."""

from django.urls import path
from apps.time_tracking.views import (
    TimeTrackingDashboardView,
    TimerStartView,
    TimerStopView,
    ManualTimeLogView,
    TimeEntryDeleteView,
    TimesheetListView,
    TimesheetDetailView,
    TimesheetGenerateView,
    TimesheetSubmitView,
    TimesheetReviewView,
)

urlpatterns = [
    # Dashboard and Live Timer
    path("time/", TimeTrackingDashboardView.as_view(), name="time_dashboard"),
    path("time/timer/start/", TimerStartView.as_view(), name="timer_start"),
    path("time/timer/stop/", TimerStopView.as_view(), name="timer_stop"),
    path("time/log/", ManualTimeLogView.as_view(), name="manual_time_log"),
    path("time/entries/<uuid:entry_id>/delete/", TimeEntryDeleteView.as_view(), name="time_entry_delete"),

    # Timesheets
    path("timesheets/", TimesheetListView.as_view(), name="timesheet_list"),
    path("timesheets/generate/", TimesheetGenerateView.as_view(), name="timesheet_generate"),
    path("timesheets/<uuid:timesheet_id>/", TimesheetDetailView.as_view(), name="timesheet_detail"),
    path("timesheets/<uuid:timesheet_id>/submit/", TimesheetSubmitView.as_view(), name="timesheet_submit"),
    path("timesheets/<uuid:timesheet_id>/review/", TimesheetReviewView.as_view(), name="timesheet_review"),
]

