"""URL patterns for departments, teams, and directory."""

from django.urls import path
from apps.departments.views import (
    DepartmentListView,
    DepartmentCreateView,
    TeamListView,
    TeamCreateView,
    EmployeeDirectoryView,
)

urlpatterns = [
    path("departments/", DepartmentListView.as_view(), name="department_list"),
    path("departments/create/", DepartmentCreateView.as_view(), name="department_create"),
    path("teams/", TeamListView.as_view(), name="team_list"),
    path("teams/create/", TeamCreateView.as_view(), name="team_create"),
    path("directory/", EmployeeDirectoryView.as_view(), name="employee_directory"),
]

