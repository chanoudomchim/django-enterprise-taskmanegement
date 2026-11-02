"""Role-Based Access Control (RBAC) models for WorkFlow Enterprise."""

import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import TenantModel


class PermissionCodes:
    """Standard system permission identifiers."""

    # Organization
    ORG_VIEW = "org:view"
    ORG_EDIT = "org:edit"
    ORG_MANAGE_SETTINGS = "org:manage_settings"
    ORG_MANAGE_BILLING = "org:manage_billing"
    ORG_INVITE_MEMBER = "org:invite_member"
    ORG_REMOVE_MEMBER = "org:remove_member"

    # Department
    DEPT_VIEW = "dept:view"
    DEPT_CREATE = "dept:create"
    DEPT_EDIT = "dept:edit"
    DEPT_DELETE = "dept:delete"
    DEPT_MANAGE_MEMBERS = "dept:manage_members"

    # Team
    TEAM_VIEW = "team:view"
    TEAM_CREATE = "team:create"
    TEAM_EDIT = "team:edit"
    TEAM_DELETE = "team:delete"
    TEAM_MANAGE_MEMBERS = "team:manage_members"

    # Project
    PROJ_VIEW = "proj:view"
    PROJ_CREATE = "proj:create"
    PROJ_EDIT = "proj:edit"
    PROJ_DELETE = "proj:delete"
    PROJ_MANAGE_MEMBERS = "proj:manage_members"

    # Task
    TASK_VIEW = "task:view"
    TASK_CREATE = "task:create"
    TASK_EDIT = "task:edit"
    TASK_DELETE = "task:delete"
    TASK_ASSIGN = "task:assign"
    TASK_CHANGE_STATUS = "task:change_status"

    # Approvals
    APPROVAL_VIEW = "approval:view"
    APPROVAL_REQUEST = "approval:request"
    APPROVAL_DECIDE = "approval:decide"

    # Time Tracking
    TIME_VIEW = "time:view"
    TIME_LOG = "time:log"
    TIME_APPROVE = "time:approve"

    # Reports
    REPORT_VIEW = "report:view"
    REPORT_EXPORT = "report:export"

    # Integrations
    INTEGRATION_VIEW = "integration:view"
    INTEGRATION_MANAGE = "integration:manage"

    # Admin
    ADMIN_ALL = "admin:all"

    @classmethod
    def choices(cls):
        return [
            (val, val)
            for key, val in cls.__dict__.items()
            if not key.startswith("__") and isinstance(val, str)
        ]


class OrganizationRole(TenantModel):
    """Organization-scoped custom or system role."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True)
    is_system_role = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("organization role")
        verbose_name_plural = _("organization roles")
        unique_together = [("organization", "slug")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def has_permission(self, permission_code):
        """Check if role holds a specific permission or admin wildcard."""
        if self.permissions.filter(permission_code=PermissionCodes.ADMIN_ALL).exists():
            return True
        return self.permissions.filter(permission_code=permission_code).exists()


class RolePermission(models.Model):
    """Specific permission mapped to a role."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        OrganizationRole,
        on_delete=models.CASCADE,
        related_name="permissions",
        db_index=True,
    )
    permission_code = models.CharField(max_length=64, choices=PermissionCodes.choices(), db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("role permission")
        verbose_name_plural = _("role permissions")
        unique_together = [("role", "permission_code")]

    def __str__(self):
        return f"{self.role.name} -> {self.permission_code}"


class UserRoleAssignment(TenantModel):
    """User assignment to a specific role within an organization."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_assignments",
        db_index=True,
    )
    role = models.ForeignKey(
        OrganizationRole,
        on_delete=models.CASCADE,
        related_name="user_assignments",
        db_index=True,
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("user role assignment")
        verbose_name_plural = _("user role assignments")
        unique_together = [("organization", "user", "role")]

    def __str__(self):
        return f"{self.user.email} as {self.role.name} in {self.organization.name}"
