"""Test healthcheck endpoint."""

from django.test import TestCase, Client
from django.urls import reverse


class HealthCheckTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_check_endpoint(self):
        """Health endpoint should return 200 with JSON payload."""
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("services", data)
        self.assertIn("database", data["services"])
        self.assertIn("redis_cache", data["services"])
        self.assertEqual(data["version"], "2.0")

    def test_home_page_loads(self):
        """Home page should render with 200."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WorkFlow Enterprise")

