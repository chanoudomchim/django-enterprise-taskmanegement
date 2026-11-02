"""Admin configuration for Tasks."""

from django.contrib import admin
from apps.tasks.models import (
    Task,
    TaskAssignment,
    TaskWatcher,
    TaskCategory,
    TaskLabel,
    TaskChecklist,
    TaskChecklistItem,
    TaskDependency,
    TaskRecurrence,
)


class TaskAssignmentInline(admin.TabularInline):
    model = TaskAssignment
    extra = 1
    raw_id_fields = ("user",)


class TaskChecklistInline(admin.TabularInline):
    model = TaskChecklist
    extra = 1


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("task_key", "title", "project", "organization", "status", "priority", "due_date")
    list_filter = ("organization", "status", "priority", "category")
    search_fields = ("title", "task_key", "description")
    inlines = [TaskAssignmentInline, TaskChecklistInline]


@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "color", "icon")


@admin.register(TaskLabel)
class TaskLabelAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "color")

