"""Test Django configuration and settings."""

from django.test import SimpleTestCase
from django.conf import settings


class SettingsTestCase(SimpleTestCase):
    def test_custom_user_model_configured(self):
        """Ensure custom accounts.User model is set before any migrations."""
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")

    def test_modular_apps_installed(self):
        """Ensure all 15 modular applications and management are in INSTALLED_APPS."""
        required_apps = [
            "management",
            "apps.accounts",
            "apps.organizations",
            "apps.rbac",
            "apps.departments",
            "apps.projects",
            "apps.tasks",
            "apps.collaboration",
            "apps.approvals",
            "apps.time_tracking",
            "apps.notifications",
            "apps.automations",
            "apps.reports",
            "apps.ai_assistant",
            "apps.integrations",
            "apps.audit",
        ]
        for app in required_apps:
            self.assertIn(app, settings.INSTALLED_APPS)

    def test_caches_configured(self):
        """Ensure default cache is configured."""
        self.assertIn("default", settings.CACHES)
        self.assertIn("BACKEND", settings.CACHES["default"])

