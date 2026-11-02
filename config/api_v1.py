"""Django REST Framework Version 1 API ViewSets and Router Configuration."""

from rest_framework import routers, viewsets, permissions, views, status, response
from rest_framework.decorators import action
from django.db.models import Count
from apps.organizations.filters import TenantFilterBackend
from apps.integrations.authentication import APIKeyAuthentication

# Models
from apps.organizations.models import Organization
from apps.departments.models import Department, Team
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.collaboration.models import Comment
from apps.approvals.models import ApprovalRequest
from apps.time_tracking.models import Timesheet, TimeEntry
from apps.notifications.models import Notification

# Serializers
from apps.accounts.serializers import UserSerializer
from apps.organizations.serializers import OrganizationSerializer
from apps.departments.serializers import DepartmentSerializer, TeamSerializer
from apps.projects.serializers import ProjectSerializer
from apps.tasks.serializers import TaskSerializer
from apps.collaboration.serializers import CommentSerializer
from apps.approvals.serializers import ApprovalRequestSerializer
from apps.time_tracking.serializers import TimesheetSerializer, TimeEntrySerializer
from apps.notifications.serializers import NotificationSerializer


class TenantModelViewSet(viewsets.ModelViewSet):
    """Base ViewSet enforcing tenant isolation and injecting active organization on save."""

    authentication_classes = [APIKeyAuthentication] + list(viewsets.ModelViewSet.authentication_classes)
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [TenantFilterBackend]

    def perform_create(self, serializer):
        serializer.save(organization=self.request.tenant)


class AuthMeView(views.APIView):
    """Returns currently authenticated user profile and active workspace."""

    authentication_classes = [APIKeyAuthentication] + list(views.APIView.authentication_classes)
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_data = UserSerializer(request.user).data
        tenant_data = OrganizationSerializer(request.tenant).data if getattr(request, "tenant", None) else None
        return response.Response({
            "user": user_data,
            "organization": tenant_data,
        })


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    """View active tenant organization details."""

    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    authentication_classes = [APIKeyAuthentication] + list(viewsets.ReadOnlyModelViewSet.authentication_classes)
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self.request, "tenant", None):
            return Organization.objects.filter(id=self.request.tenant.id)
        return Organization.objects.none()


class DepartmentViewSet(TenantModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    search_fields = ["name", "description"]


class TeamViewSet(TenantModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    search_fields = ["name", "description"]


class ProjectViewSet(TenantModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    search_fields = ["name", "key", "description"]
    filterset_fields = ["status", "priority"]


class TaskViewSet(TenantModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    search_fields = ["title", "task_key", "description"]
    filterset_fields = ["status", "priority", "project"]

    def perform_create(self, serializer):
        serializer.save(organization=self.request.tenant, created_by=self.request.user)


class CommentViewSet(TenantModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    def perform_create(self, serializer):
        serializer.save(organization=self.request.tenant, author=self.request.user)


class ApprovalRequestViewSet(TenantModelViewSet):
    queryset = ApprovalRequest.objects.all()
    serializer_class = ApprovalRequestSerializer
    filterset_fields = ["status"]

    def perform_create(self, serializer):
        from apps.approvals.services import create_approval_request
        workflow = serializer.validated_data["workflow"]
        req = create_approval_request(
            organization=self.request.tenant,
            requester=self.request.user,
            workflow=workflow,
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            task=serializer.validated_data.get("task"),
            project=serializer.validated_data.get("project"),
        )
        serializer.instance = req


class TimesheetViewSet(TenantModelViewSet):
    queryset = Timesheet.objects.all()
    serializer_class = TimesheetSerializer
    filterset_fields = ["status", "period_type"]


class NotificationViewSet(TenantModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    filterset_fields = ["is_read", "notification_type"]

    def get_queryset(self):
        return super().get_queryset().filter(recipient=self.request.user)


class ReportSummaryView(views.APIView):
    """High-level organization KPI metrics and counts."""

    authentication_classes = [APIKeyAuthentication] + list(views.APIView.authentication_classes)
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return response.Response({"error": "No active organization"}, status=status.HTTP_400_BAD_REQUEST)

        total_projects = Project.objects.filter(organization=tenant).count()
        total_tasks = Task.objects.filter(organization=tenant).count()
        completed_tasks = Task.objects.filter(organization=tenant, status="completed").count()
        pending_approvals = ApprovalRequest.objects.filter(organization=tenant, status="pending").count()

        return response.Response({
            "organization": tenant.name,
            "total_projects": total_projects,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_approvals": pending_approvals,
        })


# DRF Router Registration
api_router = routers.DefaultRouter()
api_router.register(r"organizations", OrganizationViewSet, basename="api_organizations")
api_router.register(r"departments", DepartmentViewSet, basename="api_departments")
api_router.register(r"teams", TeamViewSet, basename="api_teams")
api_router.register(r"projects", ProjectViewSet, basename="api_projects")
api_router.register(r"tasks", TaskViewSet, basename="api_tasks")
api_router.register(r"comments", CommentViewSet, basename="api_comments")
api_router.register(r"approvals", ApprovalRequestViewSet, basename="api_approvals")
api_router.register(r"timesheets", TimesheetViewSet, basename="api_timesheets")
api_router.register(r"notifications", NotificationViewSet, basename="api_notifications")

