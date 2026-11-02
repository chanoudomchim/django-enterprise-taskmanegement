"""URL patterns for Approval Management."""

from django.urls import path
from apps.approvals.views import (
    ApprovalRequestListView,
    ApprovalRequestCreateView,
    ApprovalRequestDetailView,
    ApprovalDecisionSubmitView,
    ApprovalWorkflowListView,
    ApprovalWorkflowCreateView,
)

urlpatterns = [
    path("approvals/", ApprovalRequestListView.as_view(), name="approval_request_list"),
    path("approvals/create/", ApprovalRequestCreateView.as_view(), name="approval_request_create"),
    path("approvals/<uuid:request_id>/", ApprovalRequestDetailView.as_view(), name="approval_request_detail"),
    path("approvals/<uuid:request_id>/decide/", ApprovalDecisionSubmitView.as_view(), name="approval_decision_submit"),
    path("approvals/workflows/", ApprovalWorkflowListView.as_view(), name="approval_workflow_list"),
    path("approvals/workflows/create/", ApprovalWorkflowCreateView.as_view(), name="approval_workflow_create"),
]

