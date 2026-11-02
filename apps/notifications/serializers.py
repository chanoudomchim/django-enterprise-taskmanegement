"""Serializers for Notifications."""

from rest_framework import serializers
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient",
            "actor",
            "notification_type",
            "title",
            "body",
            "task",
            "project",
            "target_url",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = ["id", "recipient", "actor", "read_at", "created_at"]

