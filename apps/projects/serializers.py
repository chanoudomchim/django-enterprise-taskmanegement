"""Serializers for Projects."""

from rest_framework import serializers
from apps.projects.models import Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "key",
            "description",
            "status",
            "priority",
            "progress_percentage",
            "start_date",
            "target_end_date",
            "actual_end_date",
            "budget",
            "owner",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "progress_percentage", "created_at", "updated_at"]

