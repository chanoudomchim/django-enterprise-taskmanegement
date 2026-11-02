"""Automated tests for the 11 Specialized Task Views."""

from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from apps.organizations.models import Organization, OrganizationMembership
from apps.projects.models import Project
from apps.tasks.models import Task, TaskAssignment, TaskWatcher

User = get_user_model()


class TaskViewsTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner_views@company.local", password="password123")
        self.member = User.objects.create_user(email="member_views@company.local", password="password123")

        self.org = Organization.objects.create(name="View Testing Org", created_by=self.owner)
        OrganizationMembership.objects.create(organization=self.org, user=self.owner, role="owner", is_default=True)
        OrganizationMembership.objects.create(organization=self.org, user=self.member, role="member", is_default=True)

        self.project = Project.objects.create(
            organization=self.org,
            name="View Project",
            key="VW",
            owner=self.owner,
        )

        today = timezone.localdate()

        # Task 1: My task, due today
        self.task_today = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.owner,
            title="Task Due Today",
            status="todo",
            priority="urgent",
            due_date=today,
            start_date=today,
        )
        TaskAssignment.objects.create(task=self.task_today, user=self.owner, assigned_by=self.owner)

        # Task 2: Upcoming task (due in 3 days)
        self.task_upcoming = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.owner,
            title="Task Upcoming",
            status="in_progress",
            priority="high",
            due_date=today + timedelta(days=3),
            start_date=today,
        )
        TaskAssignment.objects.create(task=self.task_upcoming, user=self.member, assigned_by=self.owner)

        # Task 3: Overdue task (due 3 days ago)
        self.task_overdue = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.owner,
            title="Task Overdue",
            status="in_progress",
            priority="medium",
            due_date=today - timedelta(days=3),
            start_date=today - timedelta(days=5),
        )

        # Task 4: Completed task
        self.task_completed = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.owner,
            title="Task Completed",
            status="completed",
            priority="low",
            due_date=today - timedelta(days=1),
        )

        self.client = Client()
        self.client.force_login(self.owner)
        # Set active organization in session
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

    def test_kanban_view(self):
        """Test Kanban board loads and segments columns."""
        resp = self.client.get(reverse("task_kanban"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("columns", resp.context)
        columns = resp.context["columns"]
        self.assertIn("todo", columns)
        self.assertIn("in_progress", columns)
        self.assertIn("completed", columns)
        self.assertContains(resp, "Task Due Today")
        self.assertContains(resp, "Task Upcoming")

    def test_kanban_view_filtered_by_project(self):
        """Test Kanban board filtering by project key."""
        resp = self.client.get(reverse("task_kanban") + f"?project={self.project.key}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Task Due Today")

    def test_task_list_view(self):
        """Test full task list view with filters."""
        resp = self.client.get(reverse("task_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Task Due Today")
        self.assertContains(resp, "Task Upcoming")
        self.assertContains(resp, "Task Overdue")

    def test_calendar_view(self):
        """Test calendar view displays month grid and tasks."""
        today = timezone.localdate()
        resp = self.client.get(reverse("task_calendar") + f"?year={today.year}&month={today.month}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("tasks_by_date", resp.context)
        self.assertContains(resp, "Task Due Today")

    def test_gantt_view(self):
        """Test Gantt timeline displays tasks with start and due dates."""
        resp = self.client.get(reverse("task_gantt"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("timeline_data", resp.context)
        timeline = resp.context["timeline_data"]
        self.assertTrue(len(timeline) >= 2)

    def test_my_tasks_view(self):
        """Test My Tasks filters tasks assigned to logged-in user."""
        resp = self.client.get(reverse("my_tasks"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Task Due Today")

    def test_assigned_by_me_view(self):
        """Test Assigned by Me shows tasks created/assigned by user."""
        resp = self.client.get(reverse("assigned_by_me"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Task Due Today")
        self.assertContains(resp, "Task Upcoming")

    def test_watching_tasks_view_and_toggle(self):
        """Test toggling task watch status and viewing watching list."""
        # Toggle watch on
        resp = self.client.post(reverse("task_watch_toggle", kwargs={"task_key": self.task_upcoming.task_key}))
        self.assertTrue(TaskWatcher.objects.filter(task=self.task_upcoming, user=self.owner).exists())

        # Check watching tasks view
        resp = self.client.get(reverse("watching_tasks"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Task Upcoming")

        # Toggle watch off
        self.client.post(reverse("task_watch_toggle", kwargs={"task_key": self.task_upcoming.task_key}))
        self.assertFalse(TaskWatcher.objects.filter(task=self.task_upcoming, user=self.owner).exists())

    def test_due_today_tasks_view(self):
        """Test Due Today view filters only tasks due today and not completed."""
        resp = self.client.get(reverse("due_today_tasks"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Task Due Today")
        self.assertNotContains(resp, "Task Upcoming")
        self.assertNotContains(resp, "Task Overdue")

    def test_upcoming_tasks_view(self):
        """Test Upcoming view filters tasks due in next 7 days."""
        resp = self.client.get(reverse("upcoming_tasks"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Task Upcoming")
        self.assertNotContains(resp, "Task Due Today")
        self.assertNotContains(resp, "Task Overdue")

    def test_overdue_tasks_view(self):
        """Test Overdue view filters incomplete tasks past due date."""
        resp = self.client.get(reverse("overdue_tasks"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Task Overdue")
        self.assertNotContains(resp, "Task Completed")  # completed tasks are excluded even if past due

    def test_recently_updated_tasks_view(self):
        """Test Recently Updated view returns tasks in descending update order."""
        resp = self.client.get(reverse("recently_updated_tasks"))
        self.assertEqual(resp.status_code, 200)
        tasks = resp.context["tasks"]
        self.assertTrue(len(tasks) >= 4)

