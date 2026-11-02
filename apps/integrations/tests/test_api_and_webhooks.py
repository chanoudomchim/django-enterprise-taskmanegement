"""Automated tests for REST API v1, Tenant Isolation, API Client Auth, and Webhooks."""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.management import call_command
from apps.organizations.models import Organization, OrganizationMembership
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.integrations.models import APIClient, WebhookEndpoint, WebhookDelivery
from apps.integrations.services import dispatch_webhook, retry_failed_webhooks

User = get_user_model()


class RestApiAndWebhooksTestCase(TestCase):
    def setUp(self):
        self.owner_a = User.objects.create_user(email="api_owner_a@company.local", password="password123")
        self.org_a = Organization.objects.create(name="API Org A", created_by=self.owner_a)
        OrganizationMembership.objects.create(organization=self.org_a, user=self.owner_a, role="owner", is_default=True)

        self.project_a = Project.objects.create(organization=self.org_a, name="Project Alpha", key="PRA", owner=self.owner_a)
        self.task_a = Task.objects.create(organization=self.org_a, project=self.project_a, created_by=self.owner_a, title="Alpha Task")

        # Org B (Isolated)
        self.owner_b = User.objects.create_user(email="api_owner_b@other.local", password="password123")
        self.org_b = Organization.objects.create(name="API Org B", created_by=self.owner_b)
        OrganizationMembership.objects.create(organization=self.org_b, user=self.owner_b, role="owner", is_default=True)

        self.project_b = Project.objects.create(organization=self.org_b, name="Project Beta", key="PRB", owner=self.owner_b)
        self.task_b = Task.objects.create(organization=self.org_b, project=self.project_b, created_by=self.owner_b, title="Beta Task")

        self.client_a = Client()
        self.client_a.force_login(self.owner_a)
        session = self.client_a.session
        session["active_organization_id"] = str(self.org_a.id)
        session.save()

    def test_api_tenant_isolation(self):
        """User in Org A cannot view or access tasks in Org B via REST API."""
        resp = self.client_a.get(reverse("api_tasks-list"))
        self.assertEqual(resp.status_code, 200)
        task_titles = [t["title"] for t in resp.json()["results"]]
        self.assertIn("Alpha Task", task_titles)
        self.assertNotIn("Beta Task", task_titles)

    def test_api_key_authentication(self):
        """API client credentials header authenticates and scopes tenant."""
        api_client = APIClient.objects.create(
            organization=self.org_a,
            name="CI Pipeline",
            created_by=self.owner_a,
        )

        anon_client = Client()
        # Request with valid X-API-Key and X-API-Secret
        resp = anon_client.get(
            reverse("api_auth_me"),
            HTTP_X_API_KEY=api_client.api_key,
            HTTP_X_API_SECRET=api_client.api_secret,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["organization"]["name"], "API Org A")

    def test_webhook_hmac_signing_and_dispatch(self):
        """Webhooks compute valid HMAC-SHA256 signatures."""
        endpoint = WebhookEndpoint.objects.create(
            organization=self.org_a,
            url="https://example.com/webhook",
            events=["task.created"],
        )

        payload = {"event": "task.created", "task_key": "PRA-1"}
        expected_sig = endpoint.sign_payload(payload)
        self.assertTrue(len(expected_sig) == 64)  # 64 hex characters for SHA-256

        delivery = dispatch_webhook(endpoint, "task.created", payload)
        self.assertIsNotNone(delivery)
        self.assertEqual(delivery.endpoint, endpoint)
        self.assertEqual(delivery.attempts, 1)

    def test_process_webhooks_management_command(self):
        """Process webhooks management command runs without errors."""
        endpoint = WebhookEndpoint.objects.create(
            organization=self.org_a,
            url="https://example.com/webhook",
        )
        WebhookDelivery.objects.create(
            organization=self.org_a,
            endpoint=endpoint,
            event="test.event",
            payload={"test": True},
            status="failed",
            attempts=1,
        )

        call_command("process_webhooks")
        # Delivery attempted
        d = WebhookDelivery.objects.first()
        self.assertEqual(d.attempts, 2)

