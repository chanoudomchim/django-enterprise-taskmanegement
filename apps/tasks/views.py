"""Views for Task Management and the 11 Interactive Task Views."""

import calendar
from datetime import timedelta, date
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.organizations.mixins import TenantRequiredMixin
from apps.rbac.decorators import TenantPermissionRequiredMixin
from apps.rbac.models import PermissionCodes
from apps.tasks.models import (
    Task,
    TaskAssignment,
    TaskWatcher,
    TaskChecklist,
    TaskChecklistItem,
    TaskCategory,
)
from apps.tasks.forms import TaskForm, TaskChecklistForm, TaskChecklistItemForm
from apps.collaboration.forms import CommentForm, AttachmentForm
from apps.projects.models import Project


# -------------------------------------------------------------
# 1. Standard Task CRUD & Details
# -------------------------------------------------------------

class TaskListView(TenantRequiredMixin, View):
    """View 2: Interactive List View with multi-attribute filtering."""

    def get(self, request):
        status_filter = request.GET.get("status")
        priority_filter = request.GET.get("priority")
        project_filter = request.GET.get("project")
        assignee_filter = request.GET.get("assignee")

        tasks = (
            Task.objects.filter(organization=request.tenant)
            .select_related("project", "category", "created_by")
            .prefetch_related("assignments__user", "labels")
            .order_by("position", "-created_at")
        )

        if status_filter:
            tasks = tasks.filter(status=status_filter)
        if priority_filter:
            tasks = tasks.filter(priority=priority_filter)
        if project_filter:
            tasks = tasks.filter(project__key=project_filter)
        if assignee_filter:
            tasks = tasks.filter(assignments__user_id=assignee_filter)

        projects = Project.objects.filter(organization=request.tenant)
        categories = TaskCategory.objects.filter(organization=request.tenant)

        return render(
            request,
            "tasks/task_list.html",
            {
                "tasks": tasks,
                "projects": projects,
                "categories": categories,
                "status_choices": Task.STATUS_CHOICES,
                "priority_choices": Task.PRIORITY_CHOICES,
                "current_status": status_filter,
                "current_priority": priority_filter,
                "current_project": project_filter,
                "active_tab": "list",
            },
        )


class TaskCreateView(TenantRequiredMixin, TenantPermissionRequiredMixin, View):
    """Create a new task."""

    permission_required = PermissionCodes.TASK_CREATE

    def get(self, request):
        initial = {}
        project_key = request.GET.get("project")
        if project_key:
            project = Project.objects.filter(organization=request.tenant, key=project_key).first()
            if project:
                initial["project"] = project

        form = TaskForm(organization=request.tenant, initial=initial)
        return render(request, "tasks/task_form.html", {"form": form, "title": "Create Task"})

    def post(self, request):
        form = TaskForm(request.tenant, request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.organization = request.tenant
            task.created_by = request.user
            task.save()
            form.save_m2m()

            # Assign selected users
            assignees = form.cleaned_data.get("assignees", [])
            for user in assignees:
                TaskAssignment.objects.create(
                    task=task,
                    user=user,
                    assigned_by=request.user,
                )

            messages.success(request, _(f"Task '{task.title}' [{task.task_key}] created."))
            return redirect("task_detail", task_key=task.task_key)

        return render(request, "tasks/task_form.html", {"form": form, "title": "Create Task"})


class TaskDetailView(TenantRequiredMixin, View):
    """Task details, subtasks, checklists, assignees, comments, attachments, and activities."""

    def get(self, request, task_key):
        task = get_object_or_404(
            Task.objects.select_related("project", "category", "created_by", "parent_task")
            .prefetch_related(
                "assignments__user",
                "watchers__user",
                "labels",
                "checklists__items",
                "subtasks",
                "comments__author",
                "attachments__uploaded_by",
                "activities__actor",
            ),
            organization=request.tenant,
            task_key=task_key,
        )
        checklist_form = TaskChecklistForm()
        item_form = TaskChecklistItemForm()
        comment_form = CommentForm()
        attachment_form = AttachmentForm()
        is_watching = task.watchers.filter(user=request.user).exists()

        return render(
            request,
            "tasks/task_detail.html",
            {
                "task": task,
                "checklist_form": checklist_form,
                "item_form": item_form,
                "comment_form": comment_form,
                "attachment_form": attachment_form,
                "status_choices": Task.STATUS_CHOICES,
                "is_watching": is_watching,
            },
        )


class TaskStatusUpdateView(TenantRequiredMixin, TenantPermissionRequiredMixin, View):
    """Update task status (supports HTMX and standard POST)."""

    permission_required = PermissionCodes.TASK_CHANGE_STATUS

    def post(self, request, task_key):
        task = get_object_or_404(Task, organization=request.tenant, task_key=task_key)
        new_status = request.POST.get("status")

        if new_status in dict(Task.STATUS_CHOICES):
            task.status = new_status
            task.save()
            messages.success(request, _(f"Task {task.task_key} status changed to '{task.get_status_display()}'."))

        if request.headers.get("HX-Request"):
            return render(request, "tasks/partials/kanban_card.html", {"task": task})

        next_url = request.POST.get("next") or reverse("task_detail", kwargs={"task_key": task.task_key})
        return redirect(next_url)


class TaskWatchToggleView(TenantRequiredMixin, View):
    """Toggle watcher status for current user."""

    def post(self, request, task_key):
        task = get_object_or_404(Task, organization=request.tenant, task_key=task_key)
        watcher = TaskWatcher.objects.filter(task=task, user=request.user).first()
        if watcher:
            watcher.delete()
            is_watching = False
            messages.info(request, _(f"Unwatched task {task.task_key}."))
        else:
            TaskWatcher.objects.create(task=task, user=request.user)
            is_watching = True
            messages.success(request, _(f"You are now watching task {task.task_key}."))

        if request.headers.get("HX-Request"):
            return render(
                request,
                "tasks/partials/watch_button.html",
                {"task": task, "is_watching": is_watching},
            )

        return redirect("task_detail", task_key=task.task_key)


class TaskChecklistCreateView(TenantRequiredMixin, View):
    """Add a checklist to a task."""

    def post(self, request, task_key):
        task = get_object_or_404(Task, organization=request.tenant, task_key=task_key)
        form = TaskChecklistForm(request.POST)
        if form.is_valid():
            checklist = form.save(commit=False)
            checklist.task = task
            checklist.save()
            messages.success(request, _("Checklist added."))
        return redirect("task_detail", task_key=task.task_key)


class TaskChecklistItemCreateView(TenantRequiredMixin, View):
    """Add an item to a checklist."""

    def post(self, request, checklist_id):
        checklist = get_object_or_404(TaskChecklist, id=checklist_id, task__organization=request.tenant)
        form = TaskChecklistItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.checklist = checklist
            item.save()
            messages.success(request, _("Checklist item added."))
        return redirect("task_detail", task_key=checklist.task.task_key)


class TaskChecklistItemToggleView(TenantRequiredMixin, View):
    """Toggle completion status of a checklist item."""

    def post(self, request, item_id):
        item = get_object_or_404(
            TaskChecklistItem,
            id=item_id,
            checklist__task__organization=request.tenant,
        )
        item.is_completed = not item.is_completed
        if item.is_completed:
            item.completed_by = request.user
            item.completed_at = timezone.now()
        else:
            item.completed_by = None
            item.completed_at = None
        item.save()

        if request.headers.get("HX-Request"):
            return JsonResponse({"completed": item.is_completed})

        return redirect("task_detail", task_key=item.checklist.task.task_key)


# -------------------------------------------------------------
# 2. Specialized Task Views (Part 10 Requirements 1 - 11)
# -------------------------------------------------------------

class TaskKanbanView(TenantRequiredMixin, View):
    """View 1: Kanban Board with columns and interactive status transitions."""

    def get(self, request):
        project_key = request.GET.get("project")
        tasks = Task.objects.filter(organization=request.tenant).select_related(
            "project", "category", "created_by"
        ).prefetch_related("assignments__user", "checklists__items").order_by("position", "-created_at")

        if project_key:
            tasks = tasks.filter(project__key=project_key)

        columns = {
            "backlog": {"label": "Backlog", "tasks": []},
            "todo": {"label": "To Do", "tasks": []},
            "in_progress": {"label": "In Progress", "tasks": []},
            "in_review": {"label": "In Review", "tasks": []},
            "blocked": {"label": "Blocked", "tasks": []},
            "completed": {"label": "Completed", "tasks": []},
        }

        for task in tasks:
            if task.status in columns:
                columns[task.status]["tasks"].append(task)

        projects = Project.objects.filter(organization=request.tenant)

        return render(
            request,
            "tasks/task_kanban.html",
            {
                "columns": columns,
                "projects": projects,
                "current_project": project_key,
                "active_tab": "kanban",
            },
        )


class TaskCalendarView(TenantRequiredMixin, View):
    """View 3: Monthly Calendar View mapping tasks by due dates."""

    def get(self, request):
        today = timezone.localdate()
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))

        # Month range
        cal = calendar.Calendar(firstweekday=6)  # Sunday start
        month_days = cal.monthdatescalendar(year, month)

        # Query tasks for the month window
        start_date = month_days[0][0]
        end_date = month_days[-1][-1]
        tasks = (
            Task.objects.filter(
                organization=request.tenant,
                due_date__gte=start_date,
                due_date__lte=end_date,
            )
            .select_related("project", "category")
            .order_by("due_date", "priority")
        )

        tasks_by_date = {}
        for t in tasks:
            d_str = t.due_date.isoformat()
            tasks_by_date.setdefault(d_str, []).append(t)

        prev_month = 12 if month == 1 else month - 1
        prev_year = year - 1 if month == 1 else year
        next_month = 1 if month == 12 else month + 1
        next_year = year + 1 if month == 12 else year

        return render(
            request,
            "tasks/task_calendar.html",
            {
                "month_name": calendar.month_name[month],
                "year": year,
                "month": month,
                "month_days": month_days,
                "tasks_by_date": tasks_by_date,
                "prev_month": prev_month,
                "prev_year": prev_year,
                "next_month": next_month,
                "next_year": next_year,
                "today": today,
                "active_tab": "calendar",
            },
        )


class TaskGanttView(TenantRequiredMixin, View):
    """View 4: Gantt Timeline visualization."""

    def get(self, request):
        project_key = request.GET.get("project")
        tasks = Task.objects.filter(
            organization=request.tenant,
            start_date__isnull=False,
            due_date__isnull=False,
        ).select_related("project").order_by("start_date", "due_date")

        if project_key:
            tasks = tasks.filter(project__key=project_key)

        projects = Project.objects.filter(organization=request.tenant)

        timeline_data = []
        for t in tasks:
            duration = max(1, (t.due_date - t.start_date).days)
            timeline_data.append({
                "task": t,
                "duration": duration,
                "start": t.start_date.isoformat(),
                "end": t.due_date.isoformat(),
            })

        return render(
            request,
            "tasks/task_gantt.html",
            {
                "timeline_data": timeline_data,
                "projects": projects,
                "current_project": project_key,
                "active_tab": "gantt",
            },
        )


class MyTasksView(TenantRequiredMixin, View):
    """View 5: My Tasks (assigned to current user)."""

    def get(self, request):
        tasks = (
            Task.objects.filter(organization=request.tenant, assignments__user=request.user)
            .select_related("project", "category")
            .prefetch_related("assignments__user")
            .order_by("due_date", "-created_at")
        )
        return render(
            request,
            "tasks/task_filtered_list.html",
            {"tasks": tasks, "view_title": "My Tasks", "active_tab": "my_tasks"},
        )


class AssignedByMeView(TenantRequiredMixin, View):
    """View 6: Tasks assigned or created by current user."""

    def get(self, request):
        tasks = (
            Task.objects.filter(
                organization=request.tenant,
                created_by=request.user,
            )
            .select_related("project", "category")
            .prefetch_related("assignments__user")
            .order_by("-created_at")
        )
        return render(
            request,
            "tasks/task_filtered_list.html",
            {"tasks": tasks, "view_title": "Assigned by Me", "active_tab": "assigned_by_me"},
        )


class WatchingTasksView(TenantRequiredMixin, View):
    """View 7: Tasks watched by current user."""

    def get(self, request):
        tasks = (
            Task.objects.filter(
                organization=request.tenant,
                watchers__user=request.user,
            )
            .select_related("project", "category")
            .prefetch_related("assignments__user")
            .order_by("-created_at")
        )
        return render(
            request,
            "tasks/task_filtered_list.html",
            {"tasks": tasks, "view_title": "Watching", "active_tab": "watching"},
        )


class DueTodayTasksView(TenantRequiredMixin, View):
    """View 8: Tasks due today."""

    def get(self, request):
        today = timezone.localdate()
        tasks = (
            Task.objects.filter(
                organization=request.tenant,
                due_date=today,
            )
            .exclude(status__in=["completed", "cancelled"])
            .select_related("project", "category")
            .prefetch_related("assignments__user")
            .order_by("priority")
        )
        return render(
            request,
            "tasks/task_filtered_list.html",
            {"tasks": tasks, "view_title": "Due Today", "active_tab": "due_today"},
        )


class UpcomingTasksView(TenantRequiredMixin, View):
    """View 9: Upcoming tasks within the next 7 days."""

    def get(self, request):
        today = timezone.localdate()
        next_week = today + timedelta(days=7)
        tasks = (
            Task.objects.filter(
                organization=request.tenant,
                due_date__gt=today,
                due_date__lte=next_week,
            )
            .exclude(status__in=["completed", "cancelled"])
            .select_related("project", "category")
            .prefetch_related("assignments__user")
            .order_by("due_date", "priority")
        )
        return render(
            request,
            "tasks/task_filtered_list.html",
            {"tasks": tasks, "view_title": "Upcoming (Next 7 Days)", "active_tab": "upcoming"},
        )


class OverdueTasksView(TenantRequiredMixin, View):
    """View 10: Overdue tasks past deadline."""

    def get(self, request):
        today = timezone.localdate()
        tasks = (
            Task.objects.filter(
                organization=request.tenant,
                due_date__lt=today,
            )
            .exclude(status__in=["completed", "cancelled"])
            .select_related("project", "category")
            .prefetch_related("assignments__user")
            .order_by("due_date", "priority")
        )
        return render(
            request,
            "tasks/task_filtered_list.html",
            {"tasks": tasks, "view_title": "Overdue Tasks", "active_tab": "overdue", "is_overdue_view": True},
        )


class RecentlyUpdatedTasksView(TenantRequiredMixin, View):
    """View 11: Recently updated tasks."""

    def get(self, request):
        tasks = (
            Task.objects.filter(organization=request.tenant)
            .select_related("project", "category")
            .prefetch_related("assignments__user")
            .order_by("-updated_at")[:25]
        )
        return render(
            request,
            "tasks/task_filtered_list.html",
            {"tasks": tasks, "view_title": "Recently Updated", "active_tab": "recently_updated"},
        )
