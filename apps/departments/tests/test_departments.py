"""Automated tests for Departments, Teams, and Directory views."""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.organizations.models import Organization, OrganizationMembership
from apps.departments.models import Department, DepartmentMembership, Team, TeamMembership
from apps.rbac.models import PermissionCodes

User = get_user_model()


class DepartmentTeamTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@acme.local", password="password123", first_name="Boss")
        self.member = User.objects.create_user(email="dev@acme.local", password="password123", first_name="Developer")

        self.org = Organization.objects.create(name="Acme Corp", created_by=self.owner)
        self.owner_mem = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.owner,
            role="owner",
            is_default=True,
        )
        self.member_mem = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.member,
            role="member",
            is_default=True,
        )

        self.client_owner = Client()
        self.client_owner.force_login(self.owner)

        self.client_member = Client()
        self.client_member.force_login(self.member)

    def test_department_creation_authorized(self):
        """Owner can create departments."""
        data = {
            "name": "Engineering",
            "code": "ENG",
            "description": "Core product engineering",
            "manager": str(self.owner.id),
        }
        response = self.client_owner.post(reverse("department_create"), data)
        self.assertRedirects(response, reverse("department_list"))

        dept = Department.objects.get(code="ENG", organization=self.org)
        self.assertEqual(dept.name, "Engineering")
        self.assertEqual(dept.manager, self.owner)

    def test_department_creation_unauthorized(self):
        """Regular member without DEPT_CREATE permission receives 403."""
        data = {
            "name": "Marketing",
            "code": "MKT",
            "description": "Marketing squad",
        }
        response = self.client_member.post(reverse("department_create"), data)
        self.assertEqual(response.status_code, 403)

    def test_team_creation_and_membership(self):
        """Create team and check team listing."""
        dept = Department.objects.create(organization=self.org, name="Operations", code="OPS")
        data = {
            "department": str(dept.id),
            "name": "DevOps Squad",
            "description": "Cloud infra and CI/CD",
            "lead": str(self.owner.id),
        }
        response = self.client_owner.post(reverse("team_create"), data)
        self.assertRedirects(response, reverse("team_list"))

        team = Team.objects.get(name="DevOps Squad", organization=self.org)
        self.assertEqual(team.department, dept)
        self.assertEqual(team.lead, self.owner)

    def test_employee_directory_search(self):
        """Directory view lists employees and filters by query."""
        response = self.client_owner.get(reverse("employee_directory"))
        self.assertContains(response, self.owner.email)
        self.assertContains(response, self.member.email)

        # Filter by Developer name
        filtered_resp = self.client_owner.get(reverse("employee_directory") + "?q=Developer")
        self.assertEqual(len(filtered_resp.context["memberships"]), 1)
        self.assertEqual(filtered_resp.context["memberships"][0].user, self.member)
