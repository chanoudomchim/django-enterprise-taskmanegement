"""Automated tests for Automation Rules, Actions, and Triggers."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, OrganizationMembership
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.automations.models import AutomationRule, AutomationAction, AutomationExecution
from apps.automations.services import fire_automation_trigger, execute_automation_rule

User = get_user_model()


class AutomationsTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="auto_owner@company.local", password="password123")
        self.org = Organization.objects.create(name="Auto Org", created_by=self.owner)
        OrganizationMembership.objects.create(organization=self.org, user=self.owner, role="owner", is_default=True)

        self.project = Project.objects.create(organization=self.org, name="Auto Project", key="AUT", owner=self.owner)
        self.task = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.owner,
            title="Auto Task",
            status="in_progress",
        )

    def test_automation_action_status_change(self):
        """Rule fires when trigger matches and changes task status."""
        rule = AutomationRule.objects.create(
            organization=self.org,
            created_by=self.owner,
            name="Move to In Review on Request",
            trigger="task_status_changed",
            conditions={"from_status": "in_progress"},
        )
        AutomationAction.objects.create(
            organization=self.org,
            rule=rule,
            action_type="change_status",
            parameters={"new_status": "in_review"},
            order=1,
        )

        context = {
            "task": self.task,
            "project": self.project,
            "from_status": "in_progress",
            "user": self.owner,
        }

        executions = fire_automation_trigger(self.org, "task_status_changed", context)
        self.assertEqual(len(executions), 1)
        self.assertEqual(executions[0].status, "success")

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "in_review")

    def test_automation_condition_mismatch_prevents_firing(self):
        """Rule does not fire if condition does not match."""
        rule = AutomationRule.objects.create(
            organization=self.org,
            created_by=self.owner,
            name="Blocker alert",
            trigger="task_status_changed",
            conditions={"from_status": "blocked"},
        )
        AutomationAction.objects.create(
            organization=self.org,
            rule=rule,
            action_type="change_status",
            parameters={"new_status": "in_review"},
        )

        context = {
            "task": self.task,
            "project": self.project,
            "from_status": "in_progress",  # Doesn't match 'blocked'
            "user": self.owner,
        }

        executions = fire_automation_trigger(self.org, "task_status_changed", context)
        self.assertEqual(len(executions), 0)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "in_progress")

