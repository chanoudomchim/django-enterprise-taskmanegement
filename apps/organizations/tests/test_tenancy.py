"""Automated tests for Multi-Tenancy and Tenant Isolation."""

from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationInvitation,
    OrganizationSettings,
)
from apps.organizations.middleware import TenantMiddleware

User = get_user_model()


class MultiTenantIsolationTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(email="alice@company-a.local", password="password123", first_name="Alice")
        self.user_b = User.objects.create_user(email="bob@company-b.local", password="password123", first_name="Bob")

        self.org_a = Organization.objects.create(name="Company A", created_by=self.user_a)
        self.org_b = Organization.objects.create(name="Company B", created_by=self.user_b)

        self.mem_a = OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role="owner",
            is_default=True,
        )
        self.mem_b = OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role="owner",
            is_default=True,
        )

        self.client_a = Client()
        self.client_a.force_login(self.user_a)

        self.client_b = Client()
        self.client_b.force_login(self.user_b)

    def test_tenant_middleware_resolves_active_organization(self):
        """Middleware should resolve user's default organization."""
        response = self.client_a.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["current_organization"], self.org_a)
        self.assertEqual(response.context["user_membership"].role, "owner")

    def test_tenant_isolation_membership_scoping(self):
        """User A should not see User B's organization in active context."""
        response = self.client_a.get(reverse("org_list"))
        self.assertContains(response, self.org_a.name)
        self.assertNotContains(response, self.org_b.name)

    def test_cross_tenant_switching_prevented(self):
        """User A cannot switch to Org B without membership."""
        response = self.client_a.post(reverse("org_switch", kwargs={"org_id": self.org_b.id}))
        # Should redirect to home with error
        self.assertRedirects(response, reverse("home"))

        # Verify active organization did not change
        session = self.client_a.session
        self.assertNotEqual(session.get("active_organization_id"), str(self.org_b.id))

    def test_authorized_organization_switching(self):
        """User can switch between multiple organizations they belong to."""
        # Add User A as member of Org B
        OrganizationMembership.objects.create(
            organization=self.org_b,
            user=self.user_a,
            role="member",
        )

        response = self.client_a.post(reverse("org_switch", kwargs={"org_id": self.org_b.id}))
        self.assertRedirects(response, reverse("home"))

        session = self.client_a.session
        self.assertEqual(session.get("active_organization_id"), str(self.org_b.id))

        # Check that page now reflects Org B
        resp_home = self.client_a.get(reverse("home"))
        self.assertEqual(resp_home.context["current_organization"], self.org_b)

    def test_organization_settings_access_control(self):
        """Only owners/admins can edit organization settings."""
        # Add User B to Org A as regular member
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.user_b,
            role="member",
        )
        # Switch User B to Org A
        self.client_b.post(reverse("org_switch", kwargs={"org_id": self.org_a.id}))

        # Member attempts to view settings
        response = self.client_b.get(reverse("org_settings"))
        self.assertEqual(response.status_code, 403)

        # Owner attempts to view settings
        response_owner = self.client_a.get(reverse("org_settings"))
        self.assertEqual(response_owner.status_code, 200)

    def test_organization_invitation_lifecycle(self):
        """Send and accept invitation."""
        invitee_email = "newhire@company-a.local"

        # Owner invites colleague
        response = self.client_a.post(
            reverse("org_invite"),
            {"email": invitee_email, "role": "member"},
        )
        self.assertRedirects(response, reverse("org_members"))

        invitation = OrganizationInvitation.objects.get(email=invitee_email)
        self.assertEqual(invitation.status, "pending")
        self.assertEqual(invitation.organization, self.org_a)

        # Invitee registers and accepts
        invitee_user = User.objects.create_user(email=invitee_email, password="password123")
        client_invitee = Client()
        client_invitee.force_login(invitee_user)

        accept_resp = client_invitee.get(reverse("invitation_accept", kwargs={"token": invitation.token}))
        self.assertRedirects(accept_resp, reverse("home"))

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "accepted")

        # Verify membership created
        membership = OrganizationMembership.objects.get(organization=self.org_a, user=invitee_user)
        self.assertEqual(membership.role, "member")
        self.assertTrue(membership.is_active)

