"""Serializers for User authentication and profiles."""

from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """User profile representation."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "is_active", "date_joined"]
        read_only_fields = ["id", "date_joined"]

