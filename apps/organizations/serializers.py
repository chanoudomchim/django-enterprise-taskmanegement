"""Serializers for Organizations and Memberships."""

from rest_framework import serializers
from apps.organizations.models import Organization, OrganizationMembership


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "primary_color", "logo", "is_active", "created_at"]
        read_only_fields = ["id", "slug", "created_at"]


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ["id", "user", "user_email", "role", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

