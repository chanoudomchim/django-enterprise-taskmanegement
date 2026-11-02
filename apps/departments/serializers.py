"""Serializers for Departments and Teams."""

from rest_framework import serializers
from apps.departments.models import Department, Team


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "slug", "description", "manager", "is_active", "created_at"]
        read_only_fields = ["id", "slug", "created_at"]


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "slug", "department", "lead", "description", "is_active", "created_at"]
        read_only_fields = ["id", "slug", "created_at"]

