"""Views for Analytics Dashboards, Department Performance, Workload, and CSV Exports."""

import csv
from datetime import timedelta
from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count, Sum, Q
from apps.organizations.mixins import TenantRequiredMixin
from apps.rbac.decorators import TenantPermissionRequiredMixin
from apps.rbac.models import PermissionCodes
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.departments.models import Department, Team
from apps.organizations.models import OrganizationMembership
from apps.time_tracking.models import TimeEntry
from apps.audit.models import AuditLog
from apps.audit.services import record_audit_log


class ReportsDashboardView(TenantRequiredMixin, TenantPermissionRequiredMixin, View):
    """Organization executive analytics overview with Chart.js aggregates."""

    permission_required = PermissionCodes.REPORT_VIEW

    def get(self, request):
        tenant = request.tenant
        today = timezone.localdate()

        # High-level KPIs
        total_employees = OrganizationMembership.objects.filter(organization=tenant, is_active=True).count()
        total_depts = Department.objects.filter(organization=tenant, is_active=True).count()

        projects = Project.objects.filter(organization=tenant)
        total_projects = projects.count()
        active_projects = projects.filter(status="in_progress").count()
        completed_projects = projects.filter(status="completed").count()

        tasks = Task.objects.filter(organization=tenant)
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status="completed").count()
        overdue_tasks = tasks.filter(due_date__lt=today).exclude(status__in=["completed", "cancelled"]).count()

        # Task Status Distribution for Chart.js
        status_counts = dict(
            tasks.values("status").annotate(count=Count("id")).values_list("status", "count")
        )
        status_labels = ["Backlog", "To Do", "In Progress", "In Review", "Blocked", "Completed"]
        status_data = [
            status_counts.get("backlog", 0),
            status_counts.get("todo", 0),
            status_counts.get("in_progress", 0),
            status_counts.get("in_review", 0),
            status_counts.get("blocked", 0),
            status_counts.get("completed", 0),
        ]

        # Priority Distribution for Chart.js
        priority_counts = dict(
            tasks.values("priority").annotate(count=Count("id")).values_list("priority", "count")
        )
        priority_labels = ["Urgent", "High", "Medium", "Low"]
        priority_data = [
            priority_counts.get("urgent", 0),
            priority_counts.get("high", 0),
            priority_counts.get("medium", 0),
            priority_counts.get("low", 0),
        ]

        return render(
            request,
            "reports/dashboard.html",
            {
                "total_employees": total_employees,
                "total_depts": total_depts,
                "total_projects": total_projects,
                "active_projects": active_projects,
                "completed_projects": completed_projects,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "overdue_tasks": overdue_tasks,
                "status_labels": status_labels,
                "status_data": status_data,
                "priority_labels": priority_labels,
                "priority_data": priority_data,
                "active_tab": "overview",
            },
        )


class DepartmentReportsView(TenantRequiredMixin, TenantPermissionRequiredMixin, View):
    """Department and Team workload metrics."""

    permission_required = PermissionCodes.REPORT_VIEW

    def get(self, request):
        departments = (
            Department.objects.filter(organization=request.tenant, is_active=True)
            .annotate(
                members_count=Count("memberships", distinct=True),
                teams_count=Count("teams", distinct=True),
            )
            .order_by("name")
        )

        return render(
            request,
            "reports/departments.html",
            {
                "departments": departments,
                "active_tab": "departments",
            },
        )


class ProjectReportsView(TenantRequiredMixin, TenantPermissionRequiredMixin, View):
    """Project delivery performance, budget tracking, and hours comparison."""

    permission_required = PermissionCodes.REPORT_VIEW

    def get(self, request):
        projects = (
            Project.objects.filter(organization=request.tenant)
            .annotate(
                tasks_count=Count("tasks", distinct=True),
                done_tasks_count=Count("tasks", filter=Q(tasks__status="completed"), distinct=True),
            )
            .order_by("-created_at")
        )

        return render(
            request,
            "reports/projects.html",
            {
                "projects": projects,
                "active_tab": "projects",
            },
        )


class WorkloadReportsView(TenantRequiredMixin, TenantPermissionRequiredMixin, View):
    """Team member workload distribution and task allocation."""

    permission_required = PermissionCodes.REPORT_VIEW

    def get(self, request):
        memberships = (
            OrganizationMembership.objects.filter(organization=request.tenant, is_active=True)
            .select_related("user")
            .annotate(
                assigned_count=Count("user__task_assignments__task", distinct=True),
            )
            .order_by("-assigned_count")
        )

        return render(
            request,
            "reports/workload.html",
            {
                "memberships": memberships,
                "active_tab": "workload",
            },
        )


class TaskExportCSVView(TenantRequiredMixin, TenantPermissionRequiredMixin, View):
    """Export organization tasks to downloadable CSV spreadsheet."""

    permission_required = PermissionCodes.REPORT_EXPORT

    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="tasks_{request.tenant.slug}_{timezone.localdate()}.csv"'

        writer = csv.writer(response)
        writer.writerow(["Key", "Title", "Project", "Status", "Priority", "Progress", "Estimated Hours", "Actual Hours", "Due Date", "Created Date"])

        tasks = (
            Task.objects.filter(organization=request.tenant)
            .select_related("project")
            .order_by("project__key", "task_key")
        )

        for t in tasks:
            writer.writerow([
                t.task_key,
                t.title,
                t.project.key,
                t.get_status_display(),
                t.get_priority_display(),
                f"{t.progress}%",
                t.estimated_hours,
                t.actual_hours,
                t.due_date.isoformat() if t.due_date else "",
                t.created_at.date().isoformat(),
            ])

        record_audit_log(
            organization=request.tenant,
            user=request.user,
            action="export",
            model_name="Task",
            object_repr=f"Exported {tasks.count()} tasks to CSV",
            request=request,
        )

        return response


class ProjectExportCSVView(TenantRequiredMixin, TenantPermissionRequiredMixin, View):
    """Export organization projects to downloadable CSV spreadsheet."""

    permission_required = PermissionCodes.REPORT_EXPORT

    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="projects_{request.tenant.slug}_{timezone.localdate()}.csv"'

        writer = csv.writer(response)
        writer.writerow(["Key", "Name", "Status", "Priority", "Progress", "Budget", "Start Date", "Target End Date"])

        projects = Project.objects.filter(organization=request.tenant).order_by("key")
        for p in projects:
            writer.writerow([
                p.key,
                p.name,
                p.get_status_display(),
                p.get_priority_display(),
                f"{p.progress_percentage}%",
                p.budget or 0,
                p.start_date.isoformat() if p.start_date else "",
                p.target_end_date.isoformat() if p.target_end_date else "",
            ])

        record_audit_log(
            organization=request.tenant,
            user=request.user,
            action="export",
            model_name="Project",
            object_repr=f"Exported {projects.count()} projects to CSV",
            request=request,
        )

        return response


class AuditLogListView(TenantRequiredMixin, TenantPermissionRequiredMixin, View):
    """Audit trail log viewer for organization compliance."""

    permission_required = PermissionCodes.ADMIN_ALL

    def get(self, request):
        logs = (
            AuditLog.objects.filter(organization=request.tenant)
            .select_related("user")
            .order_by("-created_at")[:100]
        )
        return render(
            request,
            "reports/audit_logs.html",
            {
                "logs": logs,
                "active_tab": "audit",
            },
        )

