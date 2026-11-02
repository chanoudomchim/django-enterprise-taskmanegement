"""Automated tests for Projects domain."""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.organizations.models import Organization, OrganizationMembership
from apps.projects.models import Project, ProjectMembership, ProjectMilestone

User = get_user_model()


class ProjectsTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="proj_owner@company.local", password="password123")
        self.org = Organization.objects.create(name="Project Org", created_by=self.owner)
        self.membership = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.owner,
            role="owner",
            is_default=True,
        )
        self.client = Client()
        self.client.force_login(self.owner)

    def test_project_creation_and_membership(self):
        """Creating a project assigns owner as project manager."""
        data = {
            "name": "Cloud Migration",
            "key": "MIG",
            "description": "Migrate workload to PostgreSQL",
            "status": "active",
            "priority": "high",
            "budget": "50000.00",
        }
        response = self.client.post(reverse("project_create"), data)
        self.assertRedirects(response, reverse("project_detail", kwargs={"key": "MIG"}))

        project = Project.objects.get(key="MIG", organization=self.org)
        self.assertEqual(project.name, "Cloud Migration")
        self.assertEqual(project.owner, self.owner)

        # Check membership
        pm = ProjectMembership.objects.get(project=project, user=self.owner)
        self.assertEqual(pm.role, "manager")

    def test_project_milestone_creation(self):
        """Add milestone to project."""
        project = Project.objects.create(organization=self.org, name="Platform V2", key="V2", owner=self.owner)
        data = {
            "title": "Beta Launch",
            "status": "pending",
            "description": "Initial customer preview",
        }
        response = self.client.post(reverse("project_milestone_create", kwargs={"key": project.key}), data)
        self.assertRedirects(response, reverse("project_detail", kwargs={"key": project.key}))

        milestone = ProjectMilestone.objects.get(project=project, title="Beta Launch")
        self.assertEqual(milestone.status, "pending")

