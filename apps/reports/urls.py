"""URL patterns for Reports, Analytics, Exports, and Audit Trail."""

from django.urls import path
from apps.reports.views import (
    ReportsDashboardView,
    DepartmentReportsView,
    ProjectReportsView,
    WorkloadReportsView,
    TaskExportCSVView,
    ProjectExportCSVView,
    AuditLogListView,
)

urlpatterns = [
    path("reports/", ReportsDashboardView.as_view(), name="reports_dashboard"),
    path("reports/departments/", DepartmentReportsView.as_view(), name="reports_departments"),
    path("reports/projects/", ProjectReportsView.as_view(), name="reports_projects"),
    path("reports/workload/", WorkloadReportsView.as_view(), name="reports_workload"),
    path("reports/export/tasks/csv/", TaskExportCSVView.as_view(), name="reports_export_tasks_csv"),
    path("reports/export/projects/csv/", ProjectExportCSVView.as_view(), name="reports_export_projects_csv"),
    path("audit/", AuditLogListView.as_view(), name="audit_logs"),
]

