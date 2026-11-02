"""URL patterns for projects."""

from django.urls import path
from apps.projects.views import (
    ProjectListView,
    ProjectCreateView,
    ProjectDetailView,
    ProjectMilestoneCreateView,
)

urlpatterns = [
    path("projects/", ProjectListView.as_view(), name="project_list"),
    path("projects/create/", ProjectCreateView.as_view(), name="project_create"),
    path("projects/<str:key>/", ProjectDetailView.as_view(), name="project_detail"),
    path("projects/<str:key>/milestones/create/", ProjectMilestoneCreateView.as_view(), name="project_milestone_create"),
]

