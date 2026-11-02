"""Automated tests for Time Tracking: Active Timers, Single-timer constraint, Timesheets, and Approvals."""

from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.organizations.models import Organization, OrganizationMembership
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.time_tracking.models import TimeEntry, ActiveTimer, Timesheet
from apps.time_tracking.services import (
    start_timer,
    stop_timer,
    log_manual_time,
    generate_timesheet,
    submit_timesheet,
    approve_timesheet,
    reject_timesheet,
)

User = get_user_model()


class TimeTrackingTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="time_owner@company.local", password="password123")
        self.employee = User.objects.create_user(email="developer@company.local", password="password123")

        self.org = Organization.objects.create(name="Time Org", created_by=self.owner)
        OrganizationMembership.objects.create(organization=self.org, user=self.owner, role="owner", is_default=True)
        OrganizationMembership.objects.create(organization=self.org, user=self.employee, role="member", is_default=True)

        self.project = Project.objects.create(
            organization=self.org,
            name="Clock Project",
            key="CLK",
            owner=self.owner,
        )
        self.task = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.owner,
            title="Design DB Schema",
            estimated_hours=10.0,
        )

        self.client = Client()
        self.client.force_login(self.employee)
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

    def test_single_active_timer_enforcement(self):
        """Prevent overlapping active timers for the same user."""
        timer1 = start_timer(
            user=self.employee,
            organization=self.org,
            project=self.project,
            task=self.task,
            description="Developing feature",
        )
        self.assertIsNotNone(timer1)

        # Attempting to start a second timer without stopping first raises ValidationError
        with self.assertRaises(ValidationError):
            start_timer(
                user=self.employee,
                organization=self.org,
                project=self.project,
                task=self.task,
            )

        # Stop timer
        entry = stop_timer(user=self.employee, organization=self.org)
        self.assertIsNotNone(entry)
        self.assertFalse(ActiveTimer.objects.filter(user=self.employee).exists())
        self.assertEqual(entry.task, self.task)
        self.assertEqual(entry.project, self.project)

    def test_manual_time_logging_updates_task_actual_hours(self):
        """Logging manual time accumulates task.actual_hours automatically."""
        entry1 = log_manual_time(
            user=self.employee,
            organization=self.org,
            project=self.project,
            task=self.task,
            hours=2.5,
            date=timezone.localdate(),
            description="Backend implementation",
        )
        self.task.refresh_from_db()
        self.assertEqual(float(self.task.actual_hours), 2.5)

        entry2 = log_manual_time(
            user=self.employee,
            organization=self.org,
            project=self.project,
            task=self.task,
            hours=1.5,
            date=timezone.localdate(),
            description="Unit tests",
        )
        self.task.refresh_from_db()
        self.assertEqual(float(self.task.actual_hours), 4.0)

    def test_timesheet_generation_and_approval_workflow(self):
        """Aggregate weekly timesheet, submit, and approve as manager."""
        today = timezone.localdate()
        start_date = today - timedelta(days=3)
        end_date = today + timedelta(days=3)

        log_manual_time(
            user=self.employee,
            organization=self.org,
            project=self.project,
            hours=4.0,
            date=today,
            is_billable=True,
        )

        timesheet = generate_timesheet(
            user=self.employee,
            organization=self.org,
            start_date=start_date,
            end_date=end_date,
            period_type="weekly",
        )

        self.assertEqual(float(timesheet.total_hours), 4.0)
        self.assertEqual(float(timesheet.billable_hours), 4.0)
        self.assertEqual(timesheet.status, "draft")

        # Submit timesheet
        submit_timesheet(timesheet)
        timesheet.refresh_from_db()
        self.assertEqual(timesheet.status, "submitted")

        # Manager approves timesheet
        approve_timesheet(timesheet, approver=self.owner, notes="Approved.")
        timesheet.refresh_from_db()
        self.assertEqual(timesheet.status, "approved")
        self.assertEqual(timesheet.approved_by, self.owner)
        self.assertIsNotNone(timesheet.approved_at)

    def test_time_tracking_views(self):
        """Dashboard, manual logging, and timesheet views render correctly."""
        # Dashboard
        resp = self.client.get(reverse("time_dashboard"))
        self.assertEqual(resp.status_code, 200)

        # Manual Log GET & POST
        resp_log_get = self.client.get(reverse("manual_time_log"))
        self.assertEqual(resp_log_get.status_code, 200)

        data = {
            "project": str(self.project.id),
            "hours": "3.0",
            "date": str(timezone.localdate()),
            "description": "API design",
            "is_billable": True,
        }
        resp_post = self.client.post(reverse("manual_time_log"), data)
        self.assertRedirects(resp_post, reverse("time_dashboard"))

        # Timesheet List view
        resp_ts = self.client.get(reverse("timesheet_list"))
        self.assertEqual(resp_ts.status_code, 200)

