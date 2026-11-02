"""Views for Approval Workflows, Requests, Decisions, and Stage History."""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.translation import gettext_lazy as _
from apps.organizations.mixins import TenantRequiredMixin
from apps.rbac.decorators import TenantPermissionRequiredMixin
from apps.rbac.models import PermissionCodes
from apps.approvals.models import ApprovalWorkflow, ApprovalStage, ApprovalRequest, ApprovalDecision
from apps.approvals.forms import ApprovalRequestForm, ApprovalDecisionForm, ApprovalWorkflowForm
from apps.approvals.services import create_approval_request, process_approval_decision


class ApprovalRequestListView(TenantRequiredMixin, View):
    """List approval requests: Pending action by current user, My requests, and All requests."""

    def get(self, request):
        tab = request.GET.get("tab", "pending")

        all_requests = (
            ApprovalRequest.objects.filter(organization=request.tenant)
            .select_related("workflow", "requester", "current_stage", "task", "project")
            .order_by("-created_at")
        )

        my_requests = all_requests.filter(requester=request.user)

        # Calculate requests where current user is authorized to decide
        pending_action_requests = [
            req for req in all_requests.filter(status="pending")
            if req.can_user_decide(request.user)
        ]

        if tab == "my":
            displayed_requests = my_requests
        elif tab == "all":
            displayed_requests = all_requests
        else:
            displayed_requests = pending_action_requests

        return render(
            request,
            "approvals/approval_list.html",
            {
                "requests": displayed_requests,
                "current_tab": tab,
                "pending_count": len(pending_action_requests),
                "my_count": my_requests.count(),
                "all_count": all_requests.count(),
            },
        )


class ApprovalRequestCreateView(TenantRequiredMixin, View):
    """Submit a new approval request."""

    def get(self, request):
        workflows = ApprovalWorkflow.objects.filter(organization=request.tenant, is_active=True)
        if not workflows.exists():
            messages.warning(request, _("No active approval workflows exist yet. Please create a workflow first."))
            return redirect("approval_workflow_list")

        form = ApprovalRequestForm(organization=request.tenant)
        return render(request, "approvals/approval_form.html", {"form": form, "title": "Submit Approval Request"})

    def post(self, request):
        form = ApprovalRequestForm(request.tenant, request.POST)
        if form.is_valid():
            try:
                workflow = form.cleaned_data["workflow"]
                title = form.cleaned_data["title"]
                description = form.cleaned_data.get("description", "")
                project = form.cleaned_data.get("project")
                task = form.cleaned_data.get("task")

                approval_req = create_approval_request(
                    organization=request.tenant,
                    requester=request.user,
                    workflow=workflow,
                    title=title,
                    description=description,
                    task=task,
                    project=project,
                )
                messages.success(request, _(f"Approval request '{approval_req.title}' submitted."))
                return redirect("approval_request_detail", request_id=approval_req.id)
            except ValidationError as e:
                messages.error(request, str(e))
        return render(request, "approvals/approval_form.html", {"form": form, "title": "Submit Approval Request"})


class ApprovalRequestDetailView(TenantRequiredMixin, View):
    """View details of an approval request, stages, history, and decision actions."""

    def get(self, request, request_id):
        approval_req = get_object_or_404(
            ApprovalRequest.objects.select_related("workflow", "requester", "current_stage", "task", "project"),
            organization=request.tenant,
            id=request_id,
        )
        stages = approval_req.workflow.stages.all().order_by("step_number")
        decisions = (
            approval_req.decisions.all()
            .select_related("stage", "approver")
            .order_by("-created_at")
        )

        can_decide = approval_req.can_user_decide(request.user)
        decision_form = ApprovalDecisionForm() if can_decide else None

        return render(
            request,
            "approvals/approval_detail.html",
            {
                "request_obj": approval_req,
                "stages": stages,
                "decisions": decisions,
                "can_decide": can_decide,
                "decision_form": decision_form,
            },
        )


class ApprovalDecisionSubmitView(TenantRequiredMixin, View):
    """Submit approval decision (approve, reject, request changes)."""

    def post(self, request, request_id):
        approval_req = get_object_or_404(
            ApprovalRequest,
            organization=request.tenant,
            id=request_id,
        )
        form = ApprovalDecisionForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data["decision"]
            comments = form.cleaned_data.get("comments", "")
            try:
                process_approval_decision(
                    approval_request=approval_req,
                    approver=request.user,
                    decision=decision,
                    comments=comments,
                )
                messages.success(request, _(f"Decision recorded: '{decision}'."))
            except (ValidationError, PermissionDenied) as e:
                messages.error(request, str(e))
        else:
            messages.error(request, _("Invalid decision submission."))

        return redirect("approval_request_detail", request_id=approval_req.id)


class ApprovalWorkflowListView(TenantRequiredMixin, View):
    """List configured approval workflows in the organization."""

    def get(self, request):
        workflows = (
            ApprovalWorkflow.objects.filter(organization=request.tenant)
            .select_related("project")
            .prefetch_related("stages")
            .order_by("name")
        )
        return render(
            request,
            "approvals/workflow_list.html",
            {"workflows": workflows},
        )


class ApprovalWorkflowCreateView(TenantRequiredMixin, View):
    """Create a new approval workflow."""

    def get(self, request):
        form = ApprovalWorkflowForm(organization=request.tenant)
        return render(request, "approvals/workflow_form.html", {"form": form})

    def post(self, request):
        form = ApprovalWorkflowForm(request.tenant, request.POST)
        if form.is_valid():
            workflow = form.save(commit=False)
            workflow.organization = request.tenant
            workflow.save()

            # Create standard default stage (Step 1: Manager Review)
            ApprovalStage.objects.create(
                organization=request.tenant,
                workflow=workflow,
                name="Manager Review",
                step_number=1,
            )

            messages.success(request, _(f"Workflow '{workflow.name}' created with default stage."))
            return redirect("approval_workflow_list")
        return render(request, "approvals/workflow_form.html", {"form": form})

