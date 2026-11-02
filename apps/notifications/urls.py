"""URL patterns for Notifications and Telegram Webhook."""

from django.urls import path
from apps.notifications.views import (
    NotificationListView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
    NotificationPreferencesView,
    TelegramWebhookView,
)

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification_list"),
    path("notifications/<uuid:notification_id>/read/", NotificationMarkReadView.as_view(), name="notification_mark_read"),
    path("notifications/mark-all-read/", NotificationMarkAllReadView.as_view(), name="notification_mark_all_read"),
    path("notifications/preferences/", NotificationPreferencesView.as_view(), name="notification_preferences"),
    path("notifications/telegram/webhook/<uuid:org_id>/", TelegramWebhookView.as_view(), name="telegram_webhook"),
]

