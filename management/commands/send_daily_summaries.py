"""Management command to dispatch daily task summaries to subscribed users."""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.notifications.models import NotificationPreference
from apps.notifications.services import send_notification
from apps.tasks.models import Task


class Command(BaseCommand):
    help = "Dispatch daily task summary digests to users with daily_summary_enabled."

    def handle(self, *args, **options):
        prefs = (
            NotificationPreference.objects.filter(daily_summary_enabled=True)
            .select_related("organization", "user")
        )

        sent_count = 0
        today = timezone.localdate()

        for pref in prefs:
            user = pref.user
            org = pref.organization

            open_tasks = (
                Task.objects.filter(organization=org, assignments__user=user)
                .exclude(status__in=["completed", "cancelled"])
                .order_by("due_date")
            )
            count = open_tasks.count()
            if count > 0:
                body = f"Good morning! You have {count} open task(s) in {org.name}."
                send_notification(
                    recipient=user,
                    organization=org,
                    notification_type="system",
                    title=f"Daily Summary: {count} Open Tasks",
                    body=body,
                )
                sent_count += 1

        self.stdout.write(self.style.SUCCESS(f"Dispatched {sent_count} daily summary digests."))

