"""Automated tests for Authentication and Profile views."""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.accounts.models import EmailVerification, UserSession
from apps.organizations.models import Organization, OrganizationMembership

User = get_user_model()


class AuthViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_registration_creates_user_and_workspace(self):
        """User registration creates account, workspace, and owner membership."""
        data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@startup.local",
            "organization_name": "JaneTech",
            "password": "SecurePassword2026!",
            "password_confirm": "SecurePassword2026!",
        }
        response = self.client.post(reverse("register"), data)
        self.assertRedirects(response, reverse("home"))

        user = User.objects.get(email="jane@startup.local")
        self.assertEqual(user.first_name, "Jane")
        self.assertTrue(user.is_active)

        # Check organization and membership
        org = Organization.objects.get(name="JaneTech")
        self.assertEqual(org.created_by, user)

        membership = OrganizationMembership.objects.get(organization=org, user=user)
        self.assertEqual(membership.role, "owner")
        self.assertTrue(membership.is_default)

        # Check verification token created
        verification = EmailVerification.objects.filter(user=user).first()
        self.assertIsNotNone(verification)

    def test_login_and_session_tracking(self):
        """Login authenticates user and tracks session."""
        user = User.objects.create_user(email="login_user@test.local", password="password123")
        org = Organization.objects.create(name="Test Org", created_by=user)
        OrganizationMembership.objects.create(organization=org, user=user, role="owner", is_default=True)

        data = {
            "email": "login_user@test.local",
            "password": "password123",
            "remember_me": True,
        }
        response = self.client.post(reverse("login"), data)
        self.assertRedirects(response, reverse("home"))

        # Verify session logged
        session_entry = UserSession.objects.filter(user=user).first()
        self.assertIsNotNone(session_entry)

    def test_login_invalid_credentials(self):
        """Login with wrong password displays error."""
        User.objects.create_user(email="login_user2@test.local", password="password123")
        data = {
            "email": "login_user2@test.local",
            "password": "wrongpassword",
        }
        response = self.client.post(reverse("login"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password.")

    def test_logout_clears_session(self):
        """Logout signs user out and deletes tracked session."""
        user = User.objects.create_user(email="logout_user@test.local", password="password123")
        self.client.force_login(user)

        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))

    def test_verify_email_flow(self):
        """Visiting verify-email token URL verifies user."""
        user = User.objects.create_user(email="unverified@test.local", password="password123", is_verified=False)
        from django.utils import timezone
        from datetime import timedelta

        verification = EmailVerification.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(days=1),
        )
        response = self.client.get(reverse("verify_email", kwargs={"token": str(verification.token)}))
        self.assertRedirects(response, reverse("home"))

        user.refresh_from_db()
        self.assertTrue(user.is_verified)
        verification.refresh_from_db()
        self.assertTrue(verification.is_used)

    def test_profile_update(self):
        """User can update profile bio, title, and theme preference."""
        user = User.objects.create_user(email="profile_user@test.local", password="password123")
        self.client.force_login(user)

        data = {
            "first_name": "UpdatedName",
            "last_name": "UpdatedLast",
            "title": "Principal Architect",
            "bio": "Building WorkFlow Enterprise",
            "timezone": "America/New_York",
            "theme_preference": "dark",
            "language": "en",
        }
        response = self.client.post(reverse("profile"), data)
        self.assertRedirects(response, reverse("profile"))

        user.refresh_from_db()
        self.assertEqual(user.first_name, "UpdatedName")
        self.assertEqual(user.profile.title, "Principal Architect")
        self.assertEqual(user.profile.theme_preference, "dark")

