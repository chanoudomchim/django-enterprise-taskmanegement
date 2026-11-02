"""Admin configuration for RBAC."""

from django.contrib import admin
from apps.rbac.models import OrganizationRole, RolePermission, UserRoleAssignment


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1


@admin.register(OrganizationRole)
class OrganizationRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "organization", "is_system_role")
    list_filter = ("organization", "is_system_role")
    search_fields = ("name", "slug")
    inlines = [RolePermissionInline]


@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "organization", "assigned_at")
    list_filter = ("organization", "role")
    search_fields = ("user__email", "role__name")

