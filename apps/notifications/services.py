"""Services for multi-channel notifications (In-app, Email, Telegram) and Telegram Bot commands."""

import urllib.request
import json
import logging
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from apps.notifications.models import (
    Notification,
    NotificationPreference,
    NotificationDelivery,
    TelegramAccount,
    TelegramIntegration,
)
from apps.tasks.models import Task

logger = logging.getLogger(__name__)


@transaction.atomic
def send_notification(
    recipient,
    organization,
    title,
    body,
    notification_type="system",
    actor=None,
    task=None,
    project=None,
    target_url="",
):
    """
    Dispatch notification across preferred channels (In-app, Email, Telegram).
    All delivery records are tracked in NotificationDelivery for audit and retry.
    """
    preference, _ = NotificationPreference.objects.get_or_create(
        organization=organization,
        user=recipient,
    )

    # Check notification type preference
    if notification_type == "task_assigned" and not preference.notify_on_task_assigned:
        return None
    if notification_type == "comment_mention" and not preference.notify_on_comment_mention:
        return None
    if notification_type == "task_due_reminder" and not preference.notify_on_due_date:
        return None
    if notification_type in ["approval_requested", "approval_decided"] and not preference.notify_on_approvals:
        return None

    notification = Notification.objects.create(
        organization=organization,
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        title=title,
        body=body,
        task=task,
        project=project,
        target_url=target_url,
    )

    # 1. In-App Delivery
    if preference.in_app_notifications:
        NotificationDelivery.objects.create(
            organization=organization,
            notification=notification,
            channel="in_app",
            status="sent",
            attempts=1,
            sent_at=timezone.now(),
        )

    # 2. Email Delivery
    if preference.email_notifications and recipient.email:
        delivery = NotificationDelivery.objects.create(
            organization=organization,
            notification=notification,
            channel="email",
            status="pending",
        )
        try:
            send_mail(
                subject=f"[{organization.name}] {title}",
                message=f"{body}\n\nView details: {target_url}",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@workflow.local"),
                recipient_list=[recipient.email],
                fail_silently=True,
            )
            delivery.status = "sent"
            delivery.attempts = 1
            delivery.sent_at = timezone.now()
            delivery.save(update_fields=["status", "attempts", "sent_at"])
        except Exception as e:
            delivery.status = "failed"
            delivery.attempts = 1
            delivery.last_error = str(e)
            delivery.save(update_fields=["status", "attempts", "last_error"])

    # 3. Telegram Delivery
    if preference.telegram_notifications:
        telegram_acc = TelegramAccount.objects.filter(
            organization=organization,
            user=recipient,
            is_verified=True,
        ).first()

        bot = TelegramIntegration.objects.filter(
            organization=organization,
            is_enabled=True,
        ).first()

        if telegram_acc and bot and bot.bot_token and telegram_acc.telegram_chat_id:
            delivery = NotificationDelivery.objects.create(
                organization=organization,
                notification=notification,
                channel="telegram",
                status="pending",
            )
            text = f"🔔 *{title}*\n\n{body}"
            success, err = dispatch_telegram_api(bot.bot_token, telegram_acc.telegram_chat_id, text)
            delivery.attempts = 1
            if success:
                delivery.status = "sent"
                delivery.sent_at = timezone.now()
            else:
                delivery.status = "failed"
                delivery.last_error = err
            delivery.save(update_fields=["status", "attempts", "sent_at", "last_error"])

    return notification


def dispatch_telegram_api(token, chat_id, message_text):
    """Make HTTP POST to Telegram Bot API sendMessage endpoint."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "Markdown",
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return True, ""
            return False, f"HTTP {response.status}"
    except Exception as e:
        logger.warning("Telegram dispatch error: %s", e)
        return False, str(e)


def handle_telegram_command(organization, chat_id, command_text):
    """
    Execute Telegram bot command with tenant and user authorization check.
    Supported commands: /start, /help, /mytasks, /today, /overdue.
    """
    parts = command_text.strip().split()
    cmd = parts[0].lower() if parts else ""

    if cmd == "/start":
        if len(parts) > 1:
            code = parts[1]
            account = TelegramAccount.objects.filter(
                organization=organization,
                verification_code=code,
            ).first()
            if account:
                account.telegram_chat_id = str(chat_id)
                account.is_verified = True
                account.verified_at = timezone.now()
                account.save(update_fields=["telegram_chat_id", "is_verified", "verified_at"])
                return f"✅ Linked to {account.user.email} in {organization.name} successfully!"
        return "👋 Welcome to WorkFlow Enterprise Bot. Please link your account from your workspace profile."

    if cmd == "/help":
        return (
            "🤖 *WorkFlow Enterprise Commands:*\n"
            "/mytasks - List your open tasks\n"
            "/today - Tasks due today\n"
            "/overdue - Overdue tasks\n"
            "/help - Command assistance"
        )

    # For private data commands, user must be verified
    account = TelegramAccount.objects.filter(
        organization=organization,
        telegram_chat_id=str(chat_id),
        is_verified=True,
    ).first()

    if not account:
        return "⚠️ You must verify your Telegram account in WorkFlow Enterprise settings before viewing private tasks."

    user = account.user

    if cmd == "/mytasks":
        tasks = (
            Task.objects.filter(organization=organization, assignments__user=user)
            .exclude(status__in=["completed", "cancelled"])
            .order_by("due_date", "priority")[:10]
        )
        if not tasks:
            return "🎉 You have no pending tasks assigned."
        lines = ["📋 *Your Pending Tasks:*"]
        for t in tasks:
            lines.append(f"• `[{t.task_key}]` {t.title} ({t.get_status_display()})")
        return "\n".join(lines)

    if cmd == "/today":
        today = timezone.localdate()
        tasks = (
            Task.objects.filter(organization=organization, assignments__user=user, due_date=today)
            .exclude(status__in=["completed", "cancelled"])
        )
        if not tasks:
            return "☀️ You have no tasks due today."
        lines = ["📅 *Tasks Due Today:*"]
        for t in tasks:
            lines.append(f"• `[{t.task_key}]` {t.title}")
        return "\n".join(lines)

    if cmd == "/overdue":
        today = timezone.localdate()
        tasks = (
            Task.objects.filter(organization=organization, assignments__user=user, due_date__lt=today)
            .exclude(status__in=["completed", "cancelled"])
        )
        if not tasks:
            return "✅ No overdue tasks."
        lines = ["🚨 *Overdue Tasks:*"]
        for t in tasks:
            lines.append(f"• `[{t.task_key}]` {t.title} (due {t.due_date})")
        return "\n".join(lines)

    return f"Unknown command '{cmd}'. Type /help for available commands."

