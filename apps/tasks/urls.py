"""URL patterns for tasks and the 11 specialized views."""

from django.urls import path
from apps.tasks.views import (
    TaskKanbanView,
    TaskListView,
    TaskCalendarView,
    TaskGanttView,
    MyTasksView,
    AssignedByMeView,
    WatchingTasksView,
    DueTodayTasksView,
    UpcomingTasksView,
    OverdueTasksView,
    RecentlyUpdatedTasksView,
    TaskCreateView,
    TaskDetailView,
    TaskStatusUpdateView,
    TaskWatchToggleView,
    TaskChecklistCreateView,
    TaskChecklistItemCreateView,
    TaskChecklistItemToggleView,
)

urlpatterns = [
    # 11 Enterprise Task Views
    path("tasks/", TaskListView.as_view(), name="task_list"),
    path("tasks/kanban/", TaskKanbanView.as_view(), name="task_kanban"),
    path("tasks/calendar/", TaskCalendarView.as_view(), name="task_calendar"),
    path("tasks/gantt/", TaskGanttView.as_view(), name="task_gantt"),
    path("tasks/my-tasks/", MyTasksView.as_view(), name="my_tasks"),
    path("tasks/assigned-by-me/", AssignedByMeView.as_view(), name="assigned_by_me"),
    path("tasks/watching/", WatchingTasksView.as_view(), name="watching_tasks"),
    path("tasks/due-today/", DueTodayTasksView.as_view(), name="due_today_tasks"),
    path("tasks/upcoming/", UpcomingTasksView.as_view(), name="upcoming_tasks"),
    path("tasks/overdue/", OverdueTasksView.as_view(), name="overdue_tasks"),
    path("tasks/recently-updated/", RecentlyUpdatedTasksView.as_view(), name="recently_updated_tasks"),

    # Task Management & Actions
    path("tasks/create/", TaskCreateView.as_view(), name="task_create"),
    path("tasks/<str:task_key>/", TaskDetailView.as_view(), name="task_detail"),
    path("tasks/<str:task_key>/status/", TaskStatusUpdateView.as_view(), name="task_status_update"),
    path("tasks/<str:task_key>/watch/", TaskWatchToggleView.as_view(), name="task_watch_toggle"),
    path("tasks/<str:task_key>/checklists/create/", TaskChecklistCreateView.as_view(), name="task_checklist_create"),
    path("checklists/<uuid:checklist_id>/items/create/", TaskChecklistItemCreateView.as_view(), name="task_checklist_item_create"),
    path("checklist-items/<uuid:item_id>/toggle/", TaskChecklistItemToggleView.as_view(), name="task_checklist_item_toggle"),
]
