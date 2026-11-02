"""Serializers for Time Tracking and Timesheets."""

from rest_framework import serializers
from apps.time_tracking.models import TimeEntry, Timesheet


class TimeEntrySerializer(serializers.ModelSerializer):
    hours = serializers.FloatField(read_only=True)

    class Meta:
        model = TimeEntry
        fields = [
            "id",
            "user",
            "project",
            "task",
            "description",
            "start_time",
            "end_time",
            "duration_seconds",
            "hours",
            "is_billable",
            "hourly_rate",
            "date",
            "created_at",
        ]
        read_only_fields = ["id", "hours", "created_at"]


class TimesheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timesheet
        fields = [
            "id",
            "user",
            "period_type",
            "start_date",
            "end_date",
            "status",
            "total_hours",
            "billable_hours",
            "submitted_at",
            "approved_at",
            "approved_by",
            "rejection_reason",
            "created_at",
        ]
        read_only_fields = ["id", "total_hours", "billable_hours", "submitted_at", "approved_at", "approved_by", "created_at"]

