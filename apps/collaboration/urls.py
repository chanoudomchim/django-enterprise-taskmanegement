"""URL patterns for Collaboration: Comments, Attachments, Activity, and Secure Media."""

from django.urls import path
from apps.collaboration.views import (
    CommentCreateView,
    CommentDeleteView,
    AttachmentUploadView,
    AttachmentDeleteView,
    SecureAttachmentDownloadView,
    ActivityFeedView,
)

urlpatterns = [
    # Comments
    path("comments/create/", CommentCreateView.as_view(), name="comment_create"),
    path("comments/<uuid:comment_id>/delete/", CommentDeleteView.as_view(), name="comment_delete"),

    # Attachments
    path("attachments/upload/", AttachmentUploadView.as_view(), name="attachment_upload"),
    path("attachments/<uuid:attachment_id>/delete/", AttachmentDeleteView.as_view(), name="attachment_delete"),
    path("media/secure/<uuid:attachment_id>/", SecureAttachmentDownloadView.as_view(), name="secure_attachment_download"),

    # Activity Feed
    path("activity/", ActivityFeedView.as_view(), name="activity_feed"),
]

