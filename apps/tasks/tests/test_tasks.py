"""Automated tests for Tasks, Checklists, and Assignments."""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.organizations.models import Organization, OrganizationMembership
from apps.projects.models import Project
from apps.tasks.models import Task, TaskAssignment, TaskChecklist, TaskChecklistItem

User = get_user_model()


class TasksTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="task_owner@company.local", password="password123")
        self.assignee = User.objects.create_user(email="worker@company.local", password="password123")

        self.org = Organization.objects.create(name="Task Org", created_by=self.owner)
        OrganizationMembership.objects.create(organization=self.org, user=self.owner, role="owner", is_default=True)
        OrganizationMembership.objects.create(organization=self.org, user=self.assignee, role="member", is_default=True)

        self.project = Project.objects.create(
            organization=self.org,
            name="Alpha Project",
            key="ALP",
            owner=self.owner,
        )

        self.client = Client()
        self.client.force_login(self.owner)

    def test_task_creation_and_key_generation(self):
        """Create task and verify auto-generated task key."""
        data = {
            "project": str(self.project.id),
            "title": "Build Auth Flow",
            "description": "Implement multi-tenant auth",
            "status": "todo",
            "priority": "high",
            "estimated_hours": "8.0",
            "assignees": [str(self.assignee.id)],
        }
        response = self.client.post(reverse("task_create"), data)
        task = Task.objects.get(title="Build Auth Flow")
        self.assertRedirects(response, reverse("task_detail", kwargs={"task_key": task.task_key}))

        self.assertEqual(task.task_key, "ALP-1")
        self.assertEqual(task.project, self.project)
        self.assertEqual(task.created_by, self.owner)

        # Check assignment
        assignment = TaskAssignment.objects.get(task=task, user=self.assignee)
        self.assertIsNotNone(assignment)

    def test_task_status_transition_updates_completion(self):
        """Transitioning to completed sets completion timestamp and updates project progress."""
        task = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.owner,
            title="Design DB Schema",
            status="in_progress",
        )
        self.assertIsNone(task.completed_date)
        self.assertEqual(self.project.progress_percentage, 0)

        # Transition to completed
        response = self.client.post(
            reverse("task_status_update", kwargs={"task_key": task.task_key}),
            {"status": "completed"},
        )
        self.assertRedirects(response, reverse("task_detail", kwargs={"task_key": task.task_key}))

        task.refresh_from_db()
        self.assertEqual(task.status, "completed")
        self.assertIsNotNone(task.completed_date)
        self.assertEqual(task.progress, 100)

        self.project.refresh_from_db()
        self.assertEqual(self.project.progress_percentage, 100)

    def test_checklist_and_item_toggle(self):
        """Add checklist and toggle item completion."""
        task = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.owner,
            title="Deploy release",
        )
        # Create checklist
        chk_resp = self.client.post(
            reverse("task_checklist_create", kwargs={"task_key": task.task_key}),
            {"title": "Pre-flight checks"},
        )
        self.assertRedirects(chk_resp, reverse("task_detail", kwargs={"task_key": task.task_key}))

        checklist = TaskChecklist.objects.get(task=task, title="Pre-flight checks")

        # Add item
        item_resp = self.client.post(
            reverse("task_checklist_item_create", kwargs={"checklist_id": checklist.id}),
            {"content": "Run database migrations"},
        )
        self.assertRedirects(item_resp, reverse("task_detail", kwargs={"task_key": task.task_key}))

        item = TaskChecklistItem.objects.get(checklist=checklist, content="Run database migrations")
        self.assertFalse(item.is_completed)

        # Toggle item
        toggle_resp = self.client.post(reverse("task_checklist_item_toggle", kwargs={"item_id": item.id}))
        self.assertRedirects(toggle_resp, reverse("task_detail", kwargs={"task_key": task.task_key}))

        item.refresh_from_db()
        self.assertTrue(item.is_completed)
        self.assertEqual(item.completed_by, self.owner)

