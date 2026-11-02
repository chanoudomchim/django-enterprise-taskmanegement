"""Departments and Teams domain models."""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import TenantModel


class Department(TenantModel):
    """Organizational department grouping teams and employees."""

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=32, db_index=True)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_departments",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = _("department")
        verbose_name_plural = _("departments")
        unique_together = [("organization", "code")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class DepartmentMembership(models.Model):
    """Membership of an employee in a department."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="department_memberships",
        db_index=True,
    )
    role_in_department = models.CharField(max_length=64, default="Member")
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _("department membership")
        verbose_name_plural = _("department memberships")
        unique_together = [("department", "user")]

    def __str__(self):
        return f"{self.user.email} in {self.department.name}"


class Team(TenantModel):
    """Functional working team inside or across departments."""

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teams",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="led_teams",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = _("team")
        verbose_name_plural = _("teams")
        unique_together = [("organization", "name")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    """Membership of a user in a team."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_memberships",
        db_index=True,
    )
    role_in_team = models.CharField(max_length=64, default="Member")
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _("team membership")
        verbose_name_plural = _("team memberships")
        unique_together = [("team", "user")]

    def __str__(self):
        return f"{self.user.email} in team {self.team.name}"
