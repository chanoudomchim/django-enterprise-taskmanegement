"""Services for approval workflow execution and decision handling."""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from apps.approvals.models import ApprovalRequest, ApprovalDecision, ApprovalStage
from apps.collaboration.services import log_activity


@transaction.atomic
def create_approval_request(organization, requester, workflow, title, description="", task=None, project=None):
    """Instantiate a new approval request at the first stage of the workflow."""
    first_stage = workflow.stages.order_by("step_number").first()
    if not first_stage:
        raise ValidationError("The selected workflow has no configured stages.")

    request = ApprovalRequest.objects.create(
        organization=organization,
        requester=requester,
        workflow=workflow,
        title=title,
        description=description,
        task=task,
        project=project,
        status="pending",
        current_stage=first_stage,
    )

    log_activity(
        organization=organization,
        actor=requester,
        action="created",
        description=f"Submitted approval request '{title}' under workflow '{workflow.name}'",
        task=task,
        project=project,
    )

    return request


@transaction.atomic
def process_approval_decision(approval_request, approver, decision, comments=""):
    """
    Process an approval decision (approved, rejected, changes_requested) for the current stage.
    Advances to next stage if approved, or marks completed/rejected.
    """
    if approval_request.status != "pending":
        raise ValidationError("This approval request is not pending review.")

    if not approval_request.can_user_decide(approver):
        raise PermissionDenied("You are not authorized to make decisions on the current approval stage.")

    current_stage = approval_request.current_stage
    if not current_stage:
        raise ValidationError("Request has no active stage to decide.")

    # Record decision
    decision_obj = ApprovalDecision.objects.create(
        organization=approval_request.organization,
        request=approval_request,
        stage=current_stage,
        approver=approver,
        decision=decision,
        comments=comments,
    )

    if decision == "approved":
        # Look for subsequent stage
        next_stage = (
            approval_request.workflow.stages.filter(step_number__gt=current_stage.step_number)
            .order_by("step_number")
            .first()
        )
        if next_stage:
            approval_request.current_stage = next_stage
            approval_request.save(update_fields=["current_stage", "updated_at"])
            status_desc = f"approved stage '{current_stage.name}'. Advanced to '{next_stage.name}'."
        else:
            approval_request.status = "approved"
            approval_request.completed_at = timezone.now()
            approval_request.save(update_fields=["status", "completed_at", "updated_at"])
            status_desc = f"fully approved request '{approval_request.title}'."
    elif decision == "rejected":
        approval_request.status = "rejected"
        approval_request.completed_at = timezone.now()
        approval_request.save(update_fields=["status", "completed_at", "updated_at"])
        status_desc = f"rejected request '{approval_request.title}' at stage '{current_stage.name}'."
    else:  # changes_requested
        # Request remains pending, stage unchanged, comment logged
        status_desc = f"requested changes on '{approval_request.title}' at stage '{current_stage.name}'."

    log_activity(
        organization=approval_request.organization,
        actor=approver,
        action="approved" if decision == "approved" else "rejected",
        description=f"{approver.email} {status_desc}",
        task=approval_request.task,
        project=approval_request.project,
    )

    return decision_obj

