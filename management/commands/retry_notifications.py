"""Management command to retry failed notification deliveries."""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.notifications.models import NotificationDelivery
from apps.notifications.services import dispatch_telegram_api, TelegramAccount, TelegramIntegration
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = "Retry failed email and Telegram notifications up to 3 attempts."

    def handle(self, *args, **options):
        failed_deliveries = (
            NotificationDelivery.objects.filter(status="failed", attempts__lt=3)
            .select_related("notification", "organization")
        )

        retried_count = 0
        success_count = 0

        for delivery in failed_deliveries:
            retried_count += 1
            delivery.attempts += 1
            notif = delivery.notification

            if delivery.channel == "email" and notif.recipient.email:
                try:
                    send_mail(
                        subject=f"[{delivery.organization.name}] {notif.title}",
                        message=f"{notif.body}\n\nView details: {notif.target_url}",
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@workflow.local"),
                        recipient_list=[notif.recipient.email],
                        fail_silently=False,
                    )
                    delivery.status = "sent"
                    delivery.sent_at = timezone.now()
                    delivery.last_error = ""
                    success_count += 1
                except Exception as e:
                    delivery.last_error = str(e)

            elif delivery.channel == "telegram":
                acc = TelegramAccount.objects.filter(
                    organization=delivery.organization,
                    user=notif.recipient,
                    is_verified=True,
                ).first()
                bot = TelegramIntegration.objects.filter(
                    organization=delivery.organization,
                    is_enabled=True,
                ).first()

                if acc and bot and bot.bot_token and acc.telegram_chat_id:
                    ok, err = dispatch_telegram_api(bot.bot_token, acc.telegram_chat_id, f"*{notif.title}*\n\n{notif.body}")
                    if ok:
                        delivery.status = "sent"
                        delivery.sent_at = timezone.now()
                        delivery.last_error = ""
                        success_count += 1
                    else:
                        delivery.last_error = err

            delivery.save(update_fields=["status", "attempts", "sent_at", "last_error"])

        self.stdout.write(self.style.SUCCESS(f"Retried {retried_count} deliveries ({success_count} succeeded)."))

