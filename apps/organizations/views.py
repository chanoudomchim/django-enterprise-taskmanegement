"""Views for Organization and Multi-Tenancy Management."""

from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationInvitation,
    OrganizationSettings,
)
from apps.organizations.forms import (
    OrganizationCreateForm,
    OrganizationSettingsForm,
    OrganizationInviteForm,
)
from apps.organizations.mixins import TenantRequiredMixin


class OrganizationListView(LoginRequiredMixin, View):
    """List all organizations user is a member of."""

    def get(self, request):
        memberships = OrganizationMembership.objects.filter(
            user=request.user,
            is_active=True,
            organization__is_active=True,
        ).select_related("organization")
        return render(request, "organizations/list.html", {"memberships": memberships})


class OrganizationCreateView(LoginRequiredMixin, View):
    """Create a new tenant organization."""

    def get(self, request):
        form = OrganizationCreateForm()
        return render(request, "organizations/create.html", {"form": form})

    def post(self, request):
        form = OrganizationCreateForm(request.POST, request.FILES)
        if form.is_valid():
            org = form.save(commit=False)
            org.created_by = request.user
            org.save()

            # Assign user as Owner
            OrganizationMembership.objects.create(
                organization=org,
                user=request.user,
                role="owner",
                is_default=not request.user.organization_memberships.filter(is_default=True).exists(),
            )

            # Set as active in session
            request.session["active_organization_id"] = str(org.id)
            messages.success(request, _(f"Organization '{org.name}' created successfully!"))
            return redirect("home")

        return render(request, "organizations/create.html", {"form": form})


class OrganizationSwitchView(LoginRequiredMixin, View):
    """Switch active tenant organization with strict membership authorization."""

    def post(self, request, org_id):
        # Validate that user is an active member of this organization
        membership = OrganizationMembership.objects.filter(
            user=request.user,
            organization_id=org_id,
            is_active=True,
            organization__is_active=True,
        ).first()

        if not membership:
            messages.error(request, _("You do not have access to that organization."))
            return redirect("home")

        # Switch active organization
        request.session["active_organization_id"] = str(org_id)
        messages.success(request, _(f"Switched to '{membership.organization.name}'."))
        next_url = request.POST.get("next") or request.GET.get("next") or "home"
        return redirect(next_url)

    def get(self, request, org_id):
        return self.post(request, org_id)


class OrganizationSettingsView(TenantRequiredMixin, View):
    """Manage active organization branding and feature toggles."""

    def get(self, request):
        membership = request.tenant_membership
        if membership.role not in ("owner", "admin"):
            raise PermissionDenied(_("Only owners and administrators can manage settings."))

        settings_obj, created = OrganizationSettings.objects.get_or_create(organization=request.tenant)
        form = OrganizationSettingsForm(instance=settings_obj)
        org_form = OrganizationCreateForm(instance=request.tenant)
        return render(
            request,
            "organizations/settings.html",
            {"form": form, "org_form": org_form, "organization": request.tenant},
        )

    def post(self, request):
        membership = request.tenant_membership
        if membership.role not in ("owner", "admin"):
            raise PermissionDenied(_("Only owners and administrators can manage settings."))

        settings_obj, created = OrganizationSettings.objects.get_or_create(organization=request.tenant)
        form = OrganizationSettingsForm(request.POST, instance=settings_obj)
        org_form = OrganizationCreateForm(request.POST, request.FILES, instance=request.tenant)

        if form.is_valid() and org_form.is_valid():
            form.save()
            org_form.save()
            messages.success(request, _("Organization settings saved successfully."))
            return redirect("org_settings")

        return render(
            request,
            "organizations/settings.html",
            {"form": form, "org_form": org_form, "organization": request.tenant},
        )


class OrganizationMembersView(TenantRequiredMixin, View):
    """List and manage members in active tenant."""

    def get(self, request):
        members = (
            OrganizationMembership.objects.filter(organization=request.tenant, is_active=True)
            .select_related("user", "user__profile")
            .order_by("role", "user__first_name")
        )
        invitations = OrganizationInvitation.objects.filter(
            organization=request.tenant, status="pending"
        ).order_by("-created_at")
        invite_form = OrganizationInviteForm()
        return render(
            request,
            "organizations/members.html",
            {
                "members": members,
                "invitations": invitations,
                "invite_form": invite_form,
                "can_invite": request.tenant_membership.role in ("owner", "admin")
                or request.tenant.settings.allow_member_invites,
            },
        )


class OrganizationInviteView(TenantRequiredMixin, View):
    """Send an invitation to join the organization."""

    def post(self, request):
        membership = request.tenant_membership
        if membership.role not in ("owner", "admin") and not request.tenant.settings.allow_member_invites:
            raise PermissionDenied(_("You do not have permission to invite members."))

        form = OrganizationInviteForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            role = form.cleaned_data["role"]

            # Check if user is already a member
            if OrganizationMembership.objects.filter(
                organization=request.tenant, user__email=email, is_active=True
            ).exists():
                messages.warning(request, _(f"{email} is already a member of this organization."))
                return redirect("org_members")

            invitation, created = OrganizationInvitation.objects.update_or_create(
                organization=request.tenant,
                email=email,
                defaults={
                    "role": role,
                    "status": "pending",
                    "invited_by": request.user,
                    "expires_at": timezone.now() + timedelta(days=7),
                },
            )
            messages.success(request, _(f"Invitation sent to {email}."))
            return redirect("org_members")

        messages.error(request, _("Invalid invitation form."))
        return redirect("org_members")


class InvitationAcceptView(LoginRequiredMixin, View):
    """Accept an organization invitation."""

    def get(self, request, token):
        invitation = get_object_or_404(OrganizationInvitation, token=token, status="pending")
        if invitation.is_expired:
            invitation.status = "expired"
            invitation.save()
            messages.error(request, _("This invitation has expired."))
            return redirect("home")

        # Create or activate membership
        membership, created = OrganizationMembership.objects.update_or_create(
            organization=invitation.organization,
            user=request.user,
            defaults={
                "role": invitation.role,
                "is_active": True,
            },
        )
        invitation.status = "accepted"
        invitation.save()

        # Switch to newly joined organization
        request.session["active_organization_id"] = str(invitation.organization.id)
        messages.success(request, _(f"You have joined {invitation.organization.name}!"))
        return redirect("home")

