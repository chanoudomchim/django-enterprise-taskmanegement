"""Admin configuration for Departments and Teams."""

from django.contrib import admin
from apps.departments.models import Department, DepartmentMembership, Team, TeamMembership


class DepartmentMembershipInline(admin.TabularInline):
    model = DepartmentMembership
    extra = 1
    raw_id_fields = ("user",)


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 1
    raw_id_fields = ("user",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "manager", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "code")
    inlines = [DepartmentMembershipInline]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "department", "lead", "is_active")
    list_filter = ("organization", "department", "is_active")
    search_fields = ("name",)
    inlines = [TeamMembershipInline]

