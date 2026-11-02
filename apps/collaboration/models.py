"""Collaboration models for WorkFlow Enterprise: Comments, Mentions, Attachments, Activities, and Saved Filters."""

import os
import uuid
import re
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import TenantModel

DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".bin", ".msi", ".dll", ".com", ".scr",
    ".php", ".phtml", ".py", ".pl", ".cgi", ".asp", ".aspx", ".jsp",
}

MAX_ATTACHMENT_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


def validate_attachment_file(file_obj):
    """Validate uploaded file size and extension."""
    if file_obj.size > MAX_ATTACHMENT_SIZE_BYTES:
        raise ValidationError(_("File size cannot exceed 25MB."))

    _, ext = os.path.splitext(file_obj.name)
    if ext.lower() in DANGEROUS_EXTENSIONS:
        raise ValidationError(_(f"File extension '{ext}' is not permitted for security reasons."))


class Comment(TenantModel):
    """Discussion comments on Tasks or Projects, supporting threaded replies and internal notes."""

    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comments",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="authored_comments",
    )
    content = models.TextField()
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    is_internal = models.BooleanField(
        default=False,
        help_text=_("Internal note visible only to organization staff and managers"),
    )
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("comment")
        verbose_name_plural = _("comments")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["task", "created_at"]),
            models.Index(fields=["project", "created_at"]),
        ]

    def clean(self):
        super().clean()
        if not self.task and not self.project:
            raise ValidationError(_("Comment must be attached to either a task or a project."))
        if self.task and self.task.organization_id != self.organization_id:
            raise ValidationError(_("Task organization does not match comment organization."))
        if self.project and self.project.organization_id != self.organization_id:
            raise ValidationError(_("Project organization does not match comment organization."))
        if self.parent and self.parent.organization_id != self.organization_id:
            raise ValidationError(_("Parent comment belongs to a different organization."))

    def extract_mentions(self):
        """Extract email mentions from comment text using regex pattern."""
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        return re.findall(email_pattern, self.content)

    def __str__(self):
        target = self.task.task_key if self.task else (self.project.key if self.project else "General")
        return f"Comment by {self.author.email} on [{target}]"


class CommentMention(TenantModel):
    """Tracks users explicitly tagged or mentioned in a comment."""

    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name="mentions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comment_mentions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("comment mention")
        verbose_name_plural = _("comment mentions")
        unique_together = [("comment", "user")]

    def __str__(self):
        return f"Mention of {self.user.email} in comment {self.comment_id}"


class Attachment(TenantModel):
    """Secure file attachment linked to tasks or projects."""

    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_attachments",
    )
    file = models.FileField(
        upload_to="attachments/%Y/%m/",
        validators=[validate_attachment_file],
    )
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text=_("File size in bytes"))
    mime_type = models.CharField(max_length=120, blank=True)
    is_public = models.BooleanField(
        default=False,
        help_text=_("Publicly accessible without authentication if enabled"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("attachment")
        verbose_name_plural = _("attachments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["task", "-created_at"]),
            models.Index(fields=["project", "-created_at"]),
        ]

    def clean(self):
        super().clean()
        if not self.task and not self.project:
            raise ValidationError(_("Attachment must belong to either a task or a project."))
        if self.task and self.task.organization_id != self.organization_id:
            raise ValidationError(_("Task organization does not match attachment organization."))
        if self.project and self.project.organization_id != self.organization_id:
            raise ValidationError(_("Project organization does not match attachment organization."))

    def __str__(self):
        return f"{self.file_name} ({self.file_size} bytes)"


class Activity(TenantModel):
    """Activity feed recording notable state changes, comments, and actions."""

    ACTION_CHOICES = [
        ("created", "Created"),
        ("updated", "Updated"),
        ("status_changed", "Status Changed"),
        ("commented", "Commented"),
        ("assigned", "Assigned"),
        ("attachment_added", "Attachment Added"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("activity")
        verbose_name_plural = _("activities")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["task", "-created_at"]),
            models.Index(fields=["project", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.action}] {self.description[:50]}"


class SavedFilter(TenantModel):
    """User-defined saved view/filter for tasks or projects."""

    FILTER_TYPE_CHOICES = [
        ("task", "Task Filter"),
        ("project", "Project Filter"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_filters",
    )
    name = models.CharField(max_length=100)
    filter_type = models.CharField(max_length=30, choices=FILTER_TYPE_CHOICES, default="task")
    criteria = models.JSONField(default=dict)
    is_shared = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("saved filter")
        verbose_name_plural = _("saved filters")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_filter_type_display()})"
