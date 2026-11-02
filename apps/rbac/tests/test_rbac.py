"""Automated tests for RBAC, roles, and permission assignments."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, OrganizationMembership
from apps.rbac.models import OrganizationRole, RolePermission, UserRoleAssignment, PermissionCodes
from apps.rbac.services import has_organization_permission, seed_default_organization_roles

User = get_user_model()


class RBACTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="member@company.local", password="password123")
        self.org = Organization.objects.create(name="RBAC Org")
        self.membership = OrganizationMembership.objects.create(
            organization=self.org,
            user=self.user,
            role="member",
        )

    def test_default_roles_seeded(self):
        """Organization creation should seed default system roles."""
        seed_default_organization_roles(self.org)
        roles = OrganizationRole.objects.filter(organization=self.org)
        self.assertGreaterEqual(roles.count(), 6)

        pm_role = OrganizationRole.objects.get(organization=self.org, slug="project-manager")
        self.assertTrue(pm_role.has_permission(PermissionCodes.PROJ_CREATE))
        self.assertTrue(pm_role.has_permission(PermissionCodes.TASK_ASSIGN))
        self.assertFalse(pm_role.has_permission(PermissionCodes.ADMIN_ALL))

    def test_permission_enforcement(self):
        """User without assigned role has no elevated permission."""
        seed_default_organization_roles(self.org)
        self.assertFalse(has_organization_permission(self.user, self.org, PermissionCodes.DEPT_CREATE))

        # Assign role to user
        dept_manager_role = OrganizationRole.objects.get(organization=self.org, slug="dept-manager")
        UserRoleAssignment.objects.create(organization=self.org, user=self.user, role=dept_manager_role)

        self.assertTrue(has_organization_permission(self.user, self.org, PermissionCodes.DEPT_CREATE))
        self.assertTrue(has_organization_permission(self.user, self.org, PermissionCodes.TEAM_CREATE))

    def test_owner_admin_bypass(self):
        """Organization owners automatically hold all permissions."""
        owner_user = User.objects.create_user(email="owner@company.local", password="password123")
        OrganizationMembership.objects.create(organization=self.org, user=owner_user, role="owner")

        self.assertTrue(has_organization_permission(owner_user, self.org, PermissionCodes.DEPT_DELETE))
        self.assertTrue(has_organization_permission(owner_user, self.org, PermissionCodes.ADMIN_ALL))

