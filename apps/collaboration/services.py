"""Services for collaboration, activity logging, and @mention parsing."""

import os
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.collaboration.models import Comment, CommentMention, Attachment, Activity

User = get_user_model()


def log_activity(organization, actor, action, description, task=None, project=None, changes=None):
    """Create an activity audit entry."""
    return Activity.objects.create(
        organization=organization,
        actor=actor,
        action=action,
        description=description,
        task=task,
        project=project,
        changes=changes or {},
    )


@transaction.atomic
def create_comment(organization, author, content, task=None, project=None, parent=None, is_internal=False):
    """Create comment, parse @mentions, and log activity."""
    comment = Comment.objects.create(
        organization=organization,
        author=author,
        content=content,
        task=task,
        project=project,
        parent=parent,
        is_internal=is_internal,
    )

    # Process mentions
    mentioned_emails = comment.extract_mentions()
    if mentioned_emails:
        mentioned_users = User.objects.filter(
            email__in=mentioned_emails,
            organization_memberships__organization=organization,
            organization_memberships__is_active=True,
        ).distinct()

        for user in mentioned_users:
            CommentMention.objects.get_or_create(
                organization=organization,
                comment=comment,
                user=user,
            )

    # Log activity
    target_name = task.task_key if task else (project.key if project else "General")
    log_activity(
        organization=organization,
        actor=author,
        action="commented",
        description=f"{author.email} commented on [{target_name}]: {content[:80]}",
        task=task,
        project=project,
    )

    return comment


@transaction.atomic
def create_attachment(organization, uploaded_by, file_obj, task=None, project=None, is_public=False):
    """Save an attachment, populate metadata, and log activity."""
    from apps.collaboration.models import validate_attachment_file
    validate_attachment_file(file_obj)

    file_name = os.path.basename(file_obj.name)
    file_size = file_obj.size
    mime_type = getattr(file_obj, "content_type", "")

    attachment = Attachment.objects.create(
        organization=organization,
        uploaded_by=uploaded_by,
        file=file_obj,
        file_name=file_name,
        file_size=file_size,
        mime_type=mime_type,
        task=task,
        project=project,
        is_public=is_public,
    )

    target_name = task.task_key if task else (project.key if project else "General")
    log_activity(
        organization=organization,
        actor=uploaded_by,
        action="attachment_added",
        description=f"{uploaded_by.email} uploaded '{file_name}' to [{target_name}]",
        task=task,
        project=project,
    )

    return attachment
