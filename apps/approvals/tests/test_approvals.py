"""Automated tests for Approval Workflows, Multi-Stage Execution, and Decisions."""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from apps.organizations.models import Organization, OrganizationMembership
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.approvals.models import ApprovalWorkflow, ApprovalStage, ApprovalRequest, ApprovalDecision
from apps.approvals.services import create_approval_request, process_approval_decision

User = get_user_model()


class ApprovalsTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="approvals_owner@company.local", password="password123")
        self.manager = User.objects.create_user(email="manager@company.local", password="password123")
        self.employee = User.objects.create_user(email="worker_app@company.local", password="password123")
        self.outsider = User.objects.create_user(email="outsider@external.local", password="password123")

        self.org = Organization.objects.create(name="Approvals Org", created_by=self.owner)
        OrganizationMembership.objects.create(organization=self.org, user=self.owner, role="owner", is_default=True)
        OrganizationMembership.objects.create(organization=self.org, user=self.manager, role="member", is_default=True)
        OrganizationMembership.objects.create(organization=self.org, user=self.employee, role="member", is_default=True)

        self.project = Project.objects.create(
            organization=self.org,
            name="Approval Project",
            key="APP",
            owner=self.owner,
        )
        self.task = Task.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.employee,
            title="Needs Budget Approval",
        )

        # 2-stage workflow:
        # Step 1: Manager Review
        # Step 2: Owner Final Approval
        self.workflow = ApprovalWorkflow.objects.create(
            organization=self.org,
            name="Two-Stage Capital Approval",
        )
        self.stage1 = ApprovalStage.objects.create(
            organization=self.org,
            workflow=self.workflow,
            name="Manager Review",
            step_number=1,
            assigned_approver=self.manager,
        )
        self.stage2 = ApprovalStage.objects.create(
            organization=self.org,
            workflow=self.workflow,
            name="Executive Signoff",
            step_number=2,
            assigned_approver=self.owner,
        )

        self.client = Client()
        self.client.force_login(self.manager)
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

    def test_multi_stage_approval_lifecycle(self):
        """Test complete progression through sequential stages to final approval."""
        # 1. Create Request
        req = create_approval_request(
            organization=self.org,
            requester=self.employee,
            workflow=self.workflow,
            title="Q4 Server Upgrade Budget",
            description="Purchase new test servers",
            task=self.task,
        )

        self.assertEqual(req.status, "pending")
        self.assertEqual(req.current_stage, self.stage1)
        self.assertIsNone(req.completed_at)

        # 2. Unauthorized user cannot decide
        with self.assertRaises(PermissionDenied):
            process_approval_decision(
                approval_request=req,
                approver=self.outsider,
                decision="approved",
            )

        # 3. Manager approves Stage 1
        decision1 = process_approval_decision(
            approval_request=req,
            approver=self.manager,
            decision="approved",
            comments="Budget looks reasonable, forwarding to executive.",
        )
        req.refresh_from_db()
        self.assertEqual(decision1.decision, "approved")
        self.assertEqual(req.status, "pending")
        self.assertEqual(req.current_stage, self.stage2)
        self.assertIsNone(req.completed_at)

        # 4. Owner approves Stage 2 (final)
        decision2 = process_approval_decision(
            approval_request=req,
            approver=self.owner,
            decision="approved",
            comments="Final budget approved.",
        )
        req.refresh_from_db()
        self.assertEqual(req.status, "approved")
        self.assertIsNotNone(req.completed_at)

    def test_approval_rejection_terminates_workflow(self):
        """Rejection at stage 1 terminates workflow immediately."""
        req = create_approval_request(
            organization=self.org,
            requester=self.employee,
            workflow=self.workflow,
            title="Overpriced Vendor Proposal",
        )

        process_approval_decision(
            approval_request=req,
            approver=self.manager,
            decision="rejected",
            comments="Cost exceeds limits.",
        )
        req.refresh_from_db()
        self.assertEqual(req.status, "rejected")
        self.assertIsNotNone(req.completed_at)

    def test_approval_views(self):
        """Approval list and detail views render correctly."""
        req = create_approval_request(
            organization=self.org,
            requester=self.employee,
            workflow=self.workflow,
            title="View Test Request",
        )

        # List view
        resp = self.client.get(reverse("approval_request_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "View Test Request")

        # Detail view
        detail_url = reverse("approval_request_detail", kwargs={"request_id": req.id})
        resp_detail = self.client.get(detail_url)
        self.assertEqual(resp_detail.status_code, 200)
        self.assertContains(resp_detail, "View Test Request")
        self.assertContains(resp_detail, "Manager Review")

