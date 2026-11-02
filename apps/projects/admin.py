"""Admin configuration for Projects."""

from django.contrib import admin
from apps.projects.models import Project, ProjectMembership, ProjectMilestone, ProjectTeam, ProjectTemplate


class ProjectMilestoneInline(admin.TabularInline):
    model = ProjectMilestone
    extra = 1


class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 1
    raw_id_fields = ("user",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "organization", "status", "priority", "manager", "progress_percentage")
    list_filter = ("organization", "status", "priority")
    search_fields = ("name", "key")
    inlines = [ProjectMilestoneInline, ProjectMembershipInline]


@admin.register(ProjectTemplate)
class ProjectTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "organization")

