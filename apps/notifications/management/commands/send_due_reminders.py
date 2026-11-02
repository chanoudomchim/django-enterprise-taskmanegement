"""Management command to dispatch due date reminders without Celery."""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.tasks.models import Task
from apps.notifications.models import Notification
from apps.notifications.services import send_notification


class Command(BaseCommand):
    help = "Scan tasks due soon and dispatch idempotent notification reminders."

    def handle(self, *args, **options):
        today = timezone.localdate()
        reminder_window = today + timedelta(days=1)

        tasks = (
            Task.objects.filter(
                due_date__gte=today,
                due_date__lte=reminder_window,
            )
            .exclude(status__in=["completed", "cancelled"])
            .select_related("organization", "project")
            .prefetch_related("assignments__user")
        )

        sent_count = 0
        for task in tasks:
            for assignment in task.assignments.all():
                user = assignment.user
                # Idempotency check: Don't send duplicate reminders for the same task on the same day
                already_sent = Notification.objects.filter(
                    organization=task.organization,
                    recipient=user,
                    task=task,
                    notification_type="task_due_reminder",
                    created_at__date=today,
                ).exists()

                if not already_sent:
                    send_notification(
                        recipient=user,
                        organization=task.organization,
                        notification_type="task_due_reminder",
                        title=f"Due Soon: [{task.task_key}] {task.title}",
                        body=f"Task '{task.title}' is due on {task.due_date}.",
                        task=task,
                        project=task.project,
                    )
                    sent_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully processed due reminders. Sent {sent_count} notifications."))
