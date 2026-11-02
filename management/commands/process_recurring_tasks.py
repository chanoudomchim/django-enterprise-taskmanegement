"""Management command to process and generate recurring tasks."""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.tasks.models import Task, TaskRecurrence


class Command(BaseCommand):
    help = "Generate task clones for active recurring tasks whose next_due date has arrived."

    def handle(self, *args, **options):
        today = timezone.localdate()
        due_recurrences = TaskRecurrence.objects.filter(
            is_active=True,
            next_due__lte=today,
        ).select_related("task", "task__organization", "task__project")

        processed = 0
        for rec in due_recurrences:
            task = rec.task
            # Generate the next instance
            count = Task.objects.filter(project=task.project).count() + 1
            new_key = f"{task.project.key}-{count}"

            # Calculate new due date based on frequency
            if rec.frequency == "daily":
                delta = timedelta(days=rec.interval)
            elif rec.frequency == "monthly":
                delta = timedelta(days=30 * rec.interval)
            else:  # weekly
                delta = timedelta(weeks=rec.interval)

            new_due = rec.next_due + delta

            Task.objects.create(
                organization=task.organization,
                project=task.project,
                task_key=new_key,
                title=f"{task.title}",
                description=task.description,
                status="todo",
                priority=task.priority,
                category=task.category,
                created_by=task.created_by,
                due_date=rec.next_due,
                estimated_hours=task.estimated_hours,
            )

            # Update recurrence schedule
            rec.next_due = new_due
            if rec.end_date and rec.next_due > rec.end_date:
                rec.is_active = False
            rec.save(update_fields=["next_due", "is_active"])
            processed += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully processed {processed} recurring task(s)."))

