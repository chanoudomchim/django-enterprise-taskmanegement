"""Serializers for Tasks."""

from rest_framework import serializers
from apps.tasks.models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "task_key",
            "project",
            "title",
            "description",
            "status",
            "priority",
            "progress",
            "estimated_hours",
            "actual_hours",
            "start_date",
            "due_date",
            "completed_date",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "task_key", "actual_hours", "completed_date", "created_at", "updated_at"]
