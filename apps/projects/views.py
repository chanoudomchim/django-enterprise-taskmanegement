"""Views for Project Management."""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from apps.organizations.mixins import TenantRequiredMixin
from apps.rbac.decorators import TenantPermissionRequiredMixin
from apps.rbac.models import PermissionCodes
from apps.projects.models import Project, ProjectMembership, ProjectMilestone
from apps.projects.forms import ProjectForm, ProjectMilestoneForm


class ProjectListView(TenantRequiredMixin, View):
    """List all projects in the active organization."""

    def get(self, request):
        status_filter = request.GET.get("status")
        projects = (
            Project.objects.filter(organization=request.tenant)
            .select_related("owner", "manager", "manager__profile")
            .prefetch_related("tasks", "milestones")
            .order_by("-created_at")
        )
        if status_filter:
            projects = projects.filter(status=status_filter)

        return render(
            request,
            "projects/project_list.html",
            {
                "projects": projects,
                "current_status": status_filter,
                "status_choices": Project.STATUS_CHOICES,
            },
        )


class ProjectCreateView(TenantRequiredMixin, TenantPermissionRequiredMixin, View):
    """Create a new project."""

    permission_required = PermissionCodes.PROJ_CREATE

    def get(self, request):
        form = ProjectForm(organization=request.tenant)
        return render(request, "projects/project_form.html", {"form": form, "title": "Create Project"})

    def post(self, request):
        form = ProjectForm(request.tenant, request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.organization = request.tenant
            project.owner = request.user
            project.key = project.key.upper()
            project.save()

            # Assign creator as manager
            ProjectMembership.objects.create(
                project=project,
                user=request.user,
                role="manager",
            )

            messages.success(request, _(f"Project '{project.name}' [{project.key}] created successfully."))
            return redirect("project_detail", key=project.key)

        return render(request, "projects/project_form.html", {"form": form, "title": "Create Project"})


class ProjectDetailView(TenantRequiredMixin, View):
    """Detailed project dashboard with tasks, milestones, and members."""

    def get(self, request, key):
        project = get_object_or_404(
            Project.objects.select_related("owner", "manager").prefetch_related("milestones", "memberships__user"),
            organization=request.tenant,
            key=key.upper(),
        )
        tasks = project.tasks.select_related("category", "created_by").prefetch_related("assignments__user").order_by("position", "-created_at")
        milestone_form = ProjectMilestoneForm()

        return render(
            request,
            "projects/project_detail.html",
            {
                "project": project,
                "tasks": tasks,
                "milestones": project.milestones.all(),
                "members": project.memberships.all(),
                "milestone_form": milestone_form,
            },
        )


class ProjectMilestoneCreateView(TenantRequiredMixin, TenantPermissionRequiredMixin, View):
    """Add a milestone to a project."""

    permission_required = PermissionCodes.PROJ_EDIT

    def post(self, request, key):
        project = get_object_or_404(Project, organization=request.tenant, key=key.upper())
        form = ProjectMilestoneForm(request.POST)
        if form.is_valid():
            milestone = form.save(commit=False)
            milestone.project = project
            milestone.save()
            messages.success(request, _("Milestone added."))
        return redirect("project_detail", key=project.key)

