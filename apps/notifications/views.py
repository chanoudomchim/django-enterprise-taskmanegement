"""Views for Notifications, Preferences, and Telegram Integration."""

import json
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.organizations.mixins import TenantRequiredMixin
from apps.organizations.models import Organization
from apps.notifications.models import (
    Notification,
    NotificationPreference,
    TelegramAccount,
    TelegramIntegration,
)
from apps.notifications.forms import NotificationPreferenceForm, TelegramIntegrationForm
from apps.notifications.services import handle_telegram_command, dispatch_telegram_api


class NotificationListView(TenantRequiredMixin, View):
    """View notifications with unread counters and filter options."""

    def get(self, request):
        filter_status = request.GET.get("status", "all")
        notifications = (
            Notification.objects.filter(organization=request.tenant, recipient=request.user)
            .select_related("actor", "task", "project")
            .order_by("-created_at")
        )

        unread_count = notifications.filter(is_read=False).count()

        if filter_status == "unread":
            notifications = notifications.filter(is_read=False)
        elif filter_status == "read":
            notifications = notifications.filter(is_read=True)

        return render(
            request,
            "notifications/notification_list.html",
            {
                "notifications": notifications[:50],
                "unread_count": unread_count,
                "current_status": filter_status,
            },
        )


class NotificationMarkReadView(TenantRequiredMixin, View):
    """Mark a single notification as read."""

    def post(self, request, notification_id):
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            organization=request.tenant,
            recipient=request.user,
        )
        notification.mark_as_read()

        if request.headers.get("HX-Request"):
            return HttpResponse(status=204)

        return redirect("notification_list")


class NotificationMarkAllReadView(TenantRequiredMixin, View):
    """Mark all unread notifications as read for current user."""

    def post(self, request):
        Notification.objects.filter(
            organization=request.tenant,
            recipient=request.user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())

        messages.success(request, _("All notifications marked as read."))
        return redirect("notification_list")


class NotificationPreferencesView(TenantRequiredMixin, View):
    """Configure notification channels and view Telegram linking status."""

    def get(self, request):
        preference, _ = NotificationPreference.objects.get_or_create(
            organization=request.tenant,
            user=request.user,
        )
        form = NotificationPreferenceForm(instance=preference)

        telegram_account, created = TelegramAccount.objects.get_or_create(
            organization=request.tenant,
            user=request.user,
            defaults={"verification_code": uuid.uuid4().hex[:12]},
        )

        telegram_bot = TelegramIntegration.objects.filter(
            organization=request.tenant,
        ).first()

        return render(
            request,
            "notifications/preferences.html",
            {
                "form": form,
                "telegram_account": telegram_account,
                "telegram_bot": telegram_bot,
            },
        )

    def post(self, request):
        preference, _ = NotificationPreference.objects.get_or_create(
            organization=request.tenant,
            user=request.user,
        )
        form = NotificationPreferenceForm(request.POST, instance=preference)
        if form.is_valid():
            form.save()
            messages.success(request, _("Notification preferences updated successfully."))
            return redirect("notification_preferences")

        return render(request, "notifications/preferences.html", {"form": form})


@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(View):
    """
    Webhook endpoint receiving incoming messages and commands from Telegram Bot API.
    URL: /notifications/telegram/webhook/<uuid:org_id>/
    """

    def post(self, request, org_id):
        try:
            organization = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({"error": "Organization not found"}, status=404)

        bot = TelegramIntegration.objects.filter(organization=organization, is_enabled=True).first()
        if not bot or not bot.bot_token:
            return JsonResponse({"error": "Telegram integration not enabled"}, status=400)

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        message = payload.get("message") or payload.get("edited_message")
        if not message:
            return JsonResponse({"ok": True})

        chat = message.get("chat", {})
        chat_id = chat.get("id")
        text = message.get("text", "")

        if chat_id and text:
            reply = handle_telegram_command(organization, chat_id, text)
            dispatch_telegram_api(bot.bot_token, chat_id, reply)

        return JsonResponse({"ok": True})

