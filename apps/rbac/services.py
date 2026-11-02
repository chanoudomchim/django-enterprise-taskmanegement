"""RBAC authorization services and helpers."""

from apps.rbac.models import OrganizationRole, RolePermission, UserRoleAssignment, PermissionCodes
from apps.organizations.models import OrganizationMembership


def has_organization_permission(user, organization, permission_code):
    """
    Check if a user holds a permission in the given organization.
    Superusers and organization owners/admins have full administrative bypass.
    """
    if not user or not user.is_authenticated or not organization:
        return False

    if user.is_superuser:
        return True

    membership = OrganizationMembership.objects.filter(
        organization=organization,
        user=user,
        is_active=True,
    ).first()

    if not membership:
        return False

    # Owners and Admins have full access
    if membership.role in ("owner", "admin"):
        return True

    # Check assigned custom organization roles
    assigned_roles = OrganizationRole.objects.filter(
        organization=organization,
        user_assignments__user=user,
    ).prefetch_related("permissions")

    for role in assigned_roles:
        if role.has_permission(permission_code):
            return True

    return False


def seed_default_organization_roles(organization):
    """Provision standard initial roles and permissions for a newly created organization."""
    role_definitions = [
        {
            "name": "Organization Administrator",
            "slug": "org-admin",
            "description": "Full workspace management and operational control",
            "permissions": [
                PermissionCodes.ADMIN_ALL,
            ],
        },
        {
            "name": "Department Manager",
            "slug": "dept-manager",
            "description": "Manages department resources, teams, and projects",
            "permissions": [
                PermissionCodes.DEPT_VIEW,
                PermissionCodes.DEPT_CREATE,
                PermissionCodes.DEPT_EDIT,
                PermissionCodes.DEPT_MANAGE_MEMBERS,
                PermissionCodes.TEAM_VIEW,
                PermissionCodes.TEAM_CREATE,
                PermissionCodes.TEAM_EDIT,
                PermissionCodes.TEAM_MANAGE_MEMBERS,
                PermissionCodes.PROJ_VIEW,
                PermissionCodes.PROJ_CREATE,
                PermissionCodes.PROJ_EDIT,
                PermissionCodes.PROJ_MANAGE_MEMBERS,
                PermissionCodes.TASK_VIEW,
                PermissionCodes.TASK_CREATE,
                PermissionCodes.TASK_EDIT,
                PermissionCodes.TASK_ASSIGN,
                PermissionCodes.APPROVAL_VIEW,
                PermissionCodes.APPROVAL_DECIDE,
                PermissionCodes.TIME_VIEW,
                PermissionCodes.TIME_APPROVE,
                PermissionCodes.REPORT_VIEW,
                PermissionCodes.REPORT_EXPORT,
            ],
        },
        {
            "name": "Project Manager",
            "slug": "project-manager",
            "description": "Directs projects, milestones, deadlines, and task distribution",
            "permissions": [
                PermissionCodes.PROJ_VIEW,
                PermissionCodes.PROJ_CREATE,
                PermissionCodes.PROJ_EDIT,
                PermissionCodes.PROJ_MANAGE_MEMBERS,
                PermissionCodes.TASK_VIEW,
                PermissionCodes.TASK_CREATE,
                PermissionCodes.TASK_EDIT,
                PermissionCodes.TASK_DELETE,
                PermissionCodes.TASK_ASSIGN,
                PermissionCodes.TASK_CHANGE_STATUS,
                PermissionCodes.APPROVAL_VIEW,
                PermissionCodes.APPROVAL_REQUEST,
                PermissionCodes.TIME_VIEW,
                PermissionCodes.TIME_APPROVE,
                PermissionCodes.REPORT_VIEW,
                PermissionCodes.REPORT_EXPORT,
            ],
        },
        {
            "name": "Team Leader",
            "slug": "team-lead",
            "description": "Coordinates team activities and task progress",
            "permissions": [
                PermissionCodes.TEAM_VIEW,
                PermissionCodes.PROJ_VIEW,
                PermissionCodes.TASK_VIEW,
                PermissionCodes.TASK_CREATE,
                PermissionCodes.TASK_EDIT,
                PermissionCodes.TASK_ASSIGN,
                PermissionCodes.TASK_CHANGE_STATUS,
                PermissionCodes.APPROVAL_VIEW,
                PermissionCodes.APPROVAL_REQUEST,
                PermissionCodes.TIME_VIEW,
                PermissionCodes.TIME_LOG,
            ],
        },
        {
            "name": "Employee",
            "slug": "employee",
            "description": "Standard team member creating and executing assigned work",
            "permissions": [
                PermissionCodes.PROJ_VIEW,
                PermissionCodes.TASK_VIEW,
                PermissionCodes.TASK_CREATE,
                PermissionCodes.TASK_EDIT,
                PermissionCodes.TASK_CHANGE_STATUS,
                PermissionCodes.TIME_VIEW,
                PermissionCodes.TIME_LOG,
            ],
        },
        {
            "name": "Guest",
            "slug": "guest",
            "description": "External collaborator with read-only task and project access",
            "permissions": [
                PermissionCodes.PROJ_VIEW,
                PermissionCodes.TASK_VIEW,
            ],
        },
    ]

    for r_def in role_definitions:
        role, created = OrganizationRole.objects.get_or_create(
            organization=organization,
            slug=r_def["slug"],
            defaults={
                "name": r_def["name"],
                "description": r_def["description"],
                "is_system_role": True,
            },
        )
        for perm in r_def["permissions"]:
            RolePermission.objects.get_or_create(role=role, permission_code=perm)
