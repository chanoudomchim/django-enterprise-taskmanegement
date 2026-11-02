"""Serializers for Comments."""

from rest_framework import serializers
from apps.collaboration.models import Comment


class CommentSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id",
            "task",
            "project",
            "author",
            "author_email",
            "content",
            "parent",
            "is_internal",
            "is_edited",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "author", "author_email", "is_edited", "created_at", "updated_at"]

