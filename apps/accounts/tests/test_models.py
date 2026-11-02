"""Tests for accounts models and custom User."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile, UserSession, EmailVerification
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class UserModelTestCase(TestCase):
    def test_create_user_with_email_successful(self):
        """Test creating a new user with an email is successful."""
        email = "test@workflow.local"
        password = "SecurePassword123!"
        user = User.objects.create_user(email=email, password=password, first_name="John", last_name="Doe")

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.full_name, "John Doe")
        self.assertEqual(user.short_name, "John")

    def test_create_user_profile_signal(self):
        """Test that a UserProfile is automatically created when a User is created."""
        user = User.objects.create_user(email="profile_test@workflow.local", password="password123")
        self.assertTrue(hasattr(user, "profile"))
        self.assertIsInstance(user.profile, UserProfile)
        self.assertEqual(user.profile.theme_preference, "light")

    def test_new_user_email_normalized(self):
        """Test the email for a new user is normalized."""
        email = "TeStUsEr@WorkFlow.Local"
        user = User.objects.create_user(email=email, password="password123")
        self.assertEqual(user.email, "TeStUsEr@workflow.local")

    def test_create_user_without_email_raises_error(self):
        """Test creating a user with no email raises a ValueError."""
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="password123")

    def test_create_superuser(self):
        """Test creating a superuser."""
        admin_user = User.objects.create_superuser(
            email="admin@workflow.local",
            password="AdminPassword123!",
            first_name="Admin",
            last_name="User",
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)

    def test_create_superuser_invalid_flags(self):
        """Test creating a superuser with invalid flags raises ValueError."""
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="badadmin@workflow.local",
                password="password123",
                is_staff=False,
            )
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="badadmin2@workflow.local",
                password="password123",
                is_superuser=False,
            )

    def test_email_verification_model(self):
        """Test email verification token lifecycle."""
        user = User.objects.create_user(email="verify@workflow.local", password="password123")
        verification = EmailVerification.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.assertFalse(verification.is_expired)
        self.assertFalse(verification.is_used)
        self.assertIn("Verification for", str(verification))

