"""Serializers for Approval Requests."""

from rest_framework import serializers
from apps.approvals.models import ApprovalRequest


class ApprovalRequestSerializer(serializers.ModelSerializer):
    requester_email = serializers.EmailField(source="requester.email", read_only=True)
    workflow_name = serializers.CharField(source="workflow.name", read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = [
            "id",
            "workflow",
            "workflow_name",
            "task",
            "project",
            "requester",
            "requester_email",
            "title",
            "description",
            "status",
            "current_stage",
            "created_at",
            "updated_at",
            "completed_at",
        ]
        read_only_fields = ["id", "requester", "requester_email", "status", "current_stage", "created_at", "updated_at", "completed_at"]

