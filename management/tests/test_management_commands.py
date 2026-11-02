"""Automated unit tests for management commands: seed_demo, verify_demo, clear_demo, and recurring tasks."""

from io import StringIO
from datetime import timedelta
from django.test import TestCase, override_settings
from django.core.management import call_command, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.tasks.models import Task, TaskRecurrence

User = get_user_model()


class ManagementCommandsTestCase(TestCase):
    def test_production_safety_guards(self):
        """Commands must refuse to execute when DEBUG is False unless --force-production is supplied."""
        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError) as ctx_seed:
                call_command("seed_demo")
            self.assertIn("Refusing to seed demo data in a production environment", str(ctx_seed.exception))

            with self.assertRaises(CommandError) as ctx_clear:
                call_command("clear_demo", no_input=True)
            self.assertIn("Refusing to clear demo data in a production environment", str(ctx_clear.exception))

    @override_settings(DEBUG=True)
    def test_clear_demo_command(self):
        """clear_demo safely deletes demo records and leaves production records intact."""
        # Non-demo org
        prod_org = Organization.objects.create(name="Production Org", slug="prod-org", is_demo=False)
        prod_user = User.objects.create_user(email="real@client.com", password="password123", is_demo=False)

        # Demo org
        demo_org = Organization.objects.create(name="Demo Org", slug="demo-org", is_demo=True)
        demo_user = User.objects.create_user(email="temp@workflow.local", password="password123", is_demo=True)

        out = StringIO()
        call_command("clear_demo", no_input=True, stdout=out)

        self.assertFalse(Organization.objects.filter(id=demo_org.id).exists())
        self.assertFalse(User.objects.filter(id=demo_user.id).exists())
        self.assertTrue(Organization.objects.filter(id=prod_org.id).exists())
        self.assertTrue(User.objects.filter(id=prod_user.id).exists())
        self.assertIn("Successfully deleted", out.getvalue())

    @override_settings(DEBUG=True)
    def test_seed_demo_scaled_execution(self):
        """seed_demo executes deterministically and seeds all target models with relational integrity."""
        out = StringIO()
        call_command(
            "seed_demo",
            organizations=10,
            users=100,
            departments=30,
            teams=50,
            projects=100,
            tasks=1000,
            comments=200,
            time_entries=100,
            notifications=100,
            audit_logs=100,
            approval_requests=50,
            attachments=20,
            categories=20,
            reset=True,
            stdout=out,
        )
        output = out.getvalue()
        self.assertIn("WORKFLOW ENTERPRISE DEMO SEEDING COMPLETE", output)
        self.assertIn("admin@workflow.local", output)

        # Verify key demo accounts authenticate
        admin = User.objects.get(email="admin@workflow.local")
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password("WorkflowDemo2026!"))

        owner = User.objects.get(email="owner@workflow.local")
        self.assertTrue(owner.check_password("WorkflowDemo2026!"))

        # Verify count thresholds
        self.assertGreaterEqual(Organization.objects.filter(is_demo=True).count(), 10)
        self.assertGreaterEqual(User.objects.filter(is_demo=True).count(), 100)
        self.assertGreaterEqual(Project.objects.filter(is_demo=True).count(), 100)
        self.assertGreaterEqual(Task.objects.filter(is_demo=True).count(), 1000)

        # Verify verify_demo command reports success
        verify_out = StringIO()
        with self.assertRaises(SystemExit) as exit_ctx:
            call_command("verify_demo", stdout=verify_out)
        self.assertEqual(exit_ctx.exception.code, 0)
        self.assertIn("ALL 2,080+ RECORD COUNT AND MULTI-TENANT AUDIT CHECKS PASSED", verify_out.getvalue())

    def test_process_recurring_tasks_command(self):
        """process_recurring_tasks creates new task instance and increments schedule."""
        user = User.objects.create_user(email="recurring@workflow.local", password="password123")
        org = Organization.objects.create(name="Recurring Org", slug="rec-org", is_demo=False)
        project = Project.objects.create(organization=org, name="Cron Project", key="CRON", owner=user)
        task = Task.objects.create(
            organization=org,
            project=project,
            created_by=user,
            title="Weekly Standup Agenda",
            status="completed",
        )
        today = timezone.localdate()
        rec = TaskRecurrence.objects.create(
            task=task,
            frequency="weekly",
            interval=1,
            next_due=today,
            is_active=True,
        )

        out = StringIO()
        call_command("process_recurring_tasks", stdout=out)

        self.assertIn("Successfully processed 1 recurring task", out.getvalue())
        rec.refresh_from_db()
        self.assertEqual(rec.next_due, today + timedelta(weeks=1))
        # New cloned task should exist
        clones = Task.objects.filter(project=project, title="Weekly Standup Agenda")
        self.assertEqual(clones.count(), 2)
