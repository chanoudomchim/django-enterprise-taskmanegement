"""Automated tests for Analytics Dashboards, Department Performance, CSV Exports, and Audit Trail."""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from apps.organizations.models import Organization, OrganizationMembership
from apps.projects.models import Project
from apps.tasks.models import Task, TaskAssignment
from apps.departments.models import Department, Team
from apps.audit.models import AuditLog
from apps.audit.services import record_audit_log

User = get_user_model()


class ReportsTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="report_owner@company.local", password="password123")
        self.member = User.objects.create_user(email="report_member@company.local", password="password123")

        self.org = Organization.objects.create(name="Analytics Org", created_by=self.owner)
        OrganizationMembership.objects.create(organization=self.org, user=self.owner, role="owner", is_default=True)
        OrganizationMembership.objects.create(organization=self.org, user=self.member, role="member", is_default=True)

        self.dept = Department.objects.create(organization=self.org, name="Engineering")
        self.team = Team.objects.create(organization=self.org, department=self.dept, name="Backend Team")

        self.project = Project.objects.create(
            organization=self.org,
            name="SaaS Analytics",
            key="SAN",
            owner=self.owner,
            budget=25000.0,
        )

        self.task1 = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.owner,
            title="Design Metrics API",
            status="completed",
            priority="high",
            estimated_hours=6.0,
        )
        TaskAssignment.objects.create(task=self.task1, user=self.member, assigned_by=self.owner)

        self.task2 = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.owner,
            title="Build Dashboard UI",
            status="in_progress",
            priority="medium",
            estimated_hours=8.0,
        )

        self.client = Client()
        self.client.force_login(self.owner)
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

    def test_reports_dashboard_metrics(self):
        """Dashboard renders KPIs, task status counts, and priority aggregates."""
        resp = self.client.get(reverse("reports_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_employees"], 2)
        self.assertEqual(resp.context["total_projects"], 1)
        self.assertEqual(resp.context["total_tasks"], 2)
        self.assertEqual(resp.context["completed_tasks"], 1)
        self.assertContains(resp, "Analytics & Reporting")

    def test_department_and_project_reports_views(self):
        """Department and project delivery reports render correctly."""
        resp_dept = self.client.get(reverse("reports_departments"))
        self.assertEqual(resp_dept.status_code, 200)
        self.assertContains(resp_dept, "Engineering")

        resp_proj = self.client.get(reverse("reports_projects"))
        self.assertEqual(resp_proj.status_code, 200)
        self.assertContains(resp_proj, "SaaS Analytics")

    def test_workload_reports_view(self):
        """Team workload report displays assigned task distribution."""
        resp = self.client.get(reverse("reports_workload"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "report_member@company.local")

    def test_task_csv_export_and_audit_logging(self):
        """CSV export outputs valid headers and rows, and records an AuditLog event."""
        resp = self.client.get(reverse("reports_export_tasks_csv"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn("attachment; filename=", resp["Content-Disposition"])

        content = resp.content.decode("utf-8")
        self.assertIn("Key,Title,Project,Status,Priority", content)
        self.assertIn("Design Metrics API", content)
        self.assertIn("Build Dashboard UI", content)

        # Verify audit log was recorded
        audit = AuditLog.objects.filter(organization=self.org, action="export", model_name="Task").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user, self.owner)

    def test_project_csv_export(self):
        """Project CSV export outputs project keys and budget data."""
        resp = self.client.get(reverse("reports_export_projects_csv"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
        content = resp.content.decode("utf-8")
        self.assertIn("Key,Name,Status,Priority,Progress,Budget", content)
        self.assertIn("SAN", content)
        self.assertIn("SaaS Analytics", content)

    def test_audit_log_list_view(self):
        """Audit trail list view renders security log events."""
        record_audit_log(
            organization=self.org,
            user=self.owner,
            action="login",
            model_name="User",
            object_repr="Owner session established",
        )
        resp = self.client.get(reverse("audit_logs"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Owner session established")
