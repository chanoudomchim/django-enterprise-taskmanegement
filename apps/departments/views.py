"""Views for Departments, Teams, and Employee Directory."""

from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.views import View
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from apps.organizations.mixins import TenantRequiredMixin, TenantContextMixin
from apps.rbac.decorators import TenantPermissionRequiredMixin
from apps.rbac.models import PermissionCodes
from apps.departments.models import Department, DepartmentMembership, Team, TeamMembership
from apps.departments.forms import DepartmentForm, TeamForm
from apps.organizations.models import OrganizationMembership


class DepartmentListView(TenantRequiredMixin, View):
    """List departments in active tenant organization."""

    def get(self, request):
        departments = (
            Department.objects.filter(organization=request.tenant, is_active=True)
            .select_related("manager", "manager__profile")
            .prefetch_related("teams")
            .order_by("name")
        )
        return render(request, "departments/department_list.html", {"departments": departments})


class DepartmentCreateView(TenantRequiredMixin, TenantPermissionRequiredMixin, View):
    """Create a new department."""

    permission_required = PermissionCodes.DEPT_CREATE

    def get(self, request):
        form = DepartmentForm(organization=request.tenant)
        return render(request, "departments/department_form.html", {"form": form, "title": "Create Department"})

    def post(self, request):
        form = DepartmentForm(request.tenant, request.POST)
        if form.is_valid():
            dept = form.save(commit=False)
            dept.organization = request.tenant
            dept.save()

            if dept.manager:
                DepartmentMembership.objects.get_or_create(
                    department=dept,
                    user=dept.manager,
                    defaults={"role_in_department": "Manager"},
                )

            messages.success(request, _(f"Department '{dept.name}' created successfully."))
            return redirect("department_list")

        return render(request, "departments/department_form.html", {"form": form, "title": "Create Department"})


class TeamListView(TenantRequiredMixin, View):
    """List teams in active tenant organization."""

    def get(self, request):
        teams = (
            Team.objects.filter(organization=request.tenant, is_active=True)
            .select_related("department", "lead", "lead__profile")
            .prefetch_related("memberships__user")
            .order_by("name")
        )
        return render(request, "departments/team_list.html", {"teams": teams})


class TeamCreateView(TenantRequiredMixin, TenantPermissionRequiredMixin, View):
    """Create a new team."""

    permission_required = PermissionCodes.TEAM_CREATE

    def get(self, request):
        form = TeamForm(organization=request.tenant)
        return render(request, "departments/team_form.html", {"form": form, "title": "Create Team"})

    def post(self, request):
        form = TeamForm(request.tenant, request.POST)
        if form.is_valid():
            team = form.save(commit=False)
            team.organization = request.tenant
            team.save()

            if team.lead:
                TeamMembership.objects.get_or_create(
                    team=team,
                    user=team.lead,
                    defaults={"role_in_team": "Team Lead"},
                )

            messages.success(request, _(f"Team '{team.name}' created successfully."))
            return redirect("team_list")

        return render(request, "departments/team_form.html", {"form": form, "title": "Create Team"})


class EmployeeDirectoryView(TenantRequiredMixin, View):
    """Employee directory with department/team mappings and search."""

    def get(self, request):
        query = request.GET.get("q", "").strip()
        memberships = (
            OrganizationMembership.objects.filter(
                organization=request.tenant,
                is_active=True,
            )
            .select_related("user", "user__profile")
            .prefetch_related("user__department_memberships__department", "user__team_memberships__team")
            .order_by("user__first_name")
        )

        if query:
            memberships = memberships.filter(
                models.Q(user__first_name__icontains=query)
                | models.Q(user__last_name__icontains=query)
                | models.Q(user__email__icontains=query)
            )

        return render(
            request,
            "departments/directory.html",
            {"memberships": memberships, "query": query},
        )
