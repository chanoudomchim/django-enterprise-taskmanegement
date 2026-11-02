"""Automated tests for AI Project Assistant: Generation, Confirmation, and Rate Limiting."""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError, PermissionDenied
from apps.organizations.models import Organization, OrganizationMembership
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.ai_assistant.models import (
    AIProviderConfiguration,
    AIGenerationRequest,
    AIUsageRecord,
)
from apps.ai_assistant.services import (
    run_ai_generation,
    apply_ai_generated_tasks,
    get_ai_config,
)

User = get_user_model()


class AIAssistantTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="ai_owner@company.local", password="password123")
        self.org = Organization.objects.create(name="AI Org", created_by=self.owner)
        OrganizationMembership.objects.create(organization=self.org, user=self.owner, role="owner", is_default=True)

        self.project = Project.objects.create(
            organization=self.org,
            name="Smart Health App",
            key="SHA",
            owner=self.owner,
        )

        self.client = Client()
        self.client.force_login(self.owner)
        session = self.client.session
        session["active_organization_id"] = str(self.org.id)
        session.save()

    def test_ai_task_generation_and_explicit_application(self):
        """AI generates structured tasks, which are only persisted upon explicit user confirmation."""
        prompt = "Build HIPAA-compliant telemedicine platform with WebRTC consultation."
        req = run_ai_generation(
            organization=self.org,
            user=self.owner,
            feature="generate_tasks",
            prompt=prompt,
            project=self.project,
        )

        self.assertEqual(req.status, "completed")
        self.assertFalse(req.applied)
        self.assertTrue(req.tokens_used > 0)
        tasks_data = req.structured_output.get("tasks", [])
        self.assertTrue(len(tasks_data) >= 3)

        # Database tasks should NOT be created automatically before user approval
        self.assertEqual(Task.objects.filter(project=self.project).count(), 0)

        # User confirms and applies tasks
        created = apply_ai_generated_tasks(req, self.project, self.owner)
        self.assertEqual(len(created), len(tasks_data))
        self.assertEqual(Task.objects.filter(project=self.project).count(), len(tasks_data))
        req.refresh_from_db()
        self.assertTrue(req.applied)

        # Usage record tracked
        usage = AIUsageRecord.objects.filter(organization=self.org, user=self.owner).first()
        self.assertIsNotNone(usage)
        self.assertEqual(usage.feature, "generate_tasks")

    def test_ai_disabled_organization_blocks_requests(self):
        """Disabling AI in organization configuration raises PermissionDenied."""
        config = get_ai_config(self.org)
        config.is_enabled = False
        config.save()

        with self.assertRaises(PermissionDenied):
            run_ai_generation(
                organization=self.org,
                user=self.owner,
                feature="generate_tasks",
                prompt="Test prompt",
                project=self.project,
            )

    def test_ai_rate_limiting(self):
        """Exceeding hourly rate limit raises ValidationError."""
        config = get_ai_config(self.org)
        config.rate_limit_per_hour = 1
        config.save()

        # First request succeeds
        run_ai_generation(self.org, self.owner, "generate_subtasks", "Subtask test", self.project)

        # Second request within the same hour is blocked
        with self.assertRaises(ValidationError):
            run_ai_generation(self.org, self.owner, "generate_subtasks", "Exceed limit", self.project)

    def test_ai_views(self):
        """AI console and request detail views render correctly."""
        resp_console = self.client.get(reverse("ai_console"))
        self.assertEqual(resp_console.status_code, 200)
        self.assertContains(resp_console, "AI Project Assistant")

        req = run_ai_generation(self.org, self.owner, "risk_assessment", "Evaluate risk", self.project)
        resp_detail = self.client.get(reverse("ai_request_detail", kwargs={"request_id": req.id}))
        self.assertEqual(resp_detail.status_code, 200)
        self.assertContains(resp_detail, "Risk Assessment")

