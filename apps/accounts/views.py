"""Authentication and User Profile Views."""

from datetime import timedelta
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.accounts.forms import (
    UserRegistrationForm,
    UserLoginForm,
    UserProfileForm,
    PasswordResetRequestForm,
    PasswordChangeCustomForm,
)
from apps.accounts.models import EmailVerification, UserSession
from apps.organizations.models import Organization, OrganizationMembership

User = get_user_model()


class RegisterView(View):
    """User registration flow with optional initial workspace creation."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("home")
        form = UserRegistrationForm()
        return render(request, "accounts/register.html", {"form": form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("home")
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            org_name = form.cleaned_data.get("organization_name")

            # Create default organization if specified or generate one
            if not org_name:
                org_name = f"{user.first_name or user.email.split('@')[0]}'s Workspace"

            org = Organization.objects.create(name=org_name, created_by=user)
            OrganizationMembership.objects.create(
                organization=org,
                user=user,
                role="owner",
                is_default=True,
            )

            # Create email verification token
            EmailVerification.objects.create(
                user=user,
                expires_at=timezone.now() + timedelta(days=2),
            )

            # Log user in
            login(request, user)
            request.session["active_organization_id"] = str(org.id)

            messages.success(request, _(f"Welcome to WorkFlow Enterprise! Workspace '{org.name}' created."))
            return redirect("home")

        return render(request, "accounts/register.html", {"form": form})


class LoginView(View):
    """User login flow with session tracking."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("home")
        form = UserLoginForm()
        return render(request, "accounts/login.html", {"form": form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect("home")
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)

            remember_me = form.cleaned_data.get("remember_me")
            if not remember_me:
                request.session.set_expiry(0)  # Browser close
            else:
                request.session.set_expiry(30 * 86400)  # 30 days

            # Record session
            if request.session.session_key:
                UserSession.objects.create(
                    user=user,
                    session_key=request.session.session_key,
                    ip_address=request.META.get("REMOTE_ADDR"),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                )

            messages.success(request, _(f"Welcome back, {user.first_name or user.email}!"))
            next_url = request.GET.get("next") or "home"
            return redirect(next_url)

        return render(request, "accounts/login.html", {"form": form})


class LogoutView(View):
    """User logout."""

    def post(self, request):
        if request.user.is_authenticated and request.session.session_key:
            UserSession.objects.filter(session_key=request.session.session_key).delete()
        logout(request)
        messages.info(request, _("You have been signed out successfully."))
        return redirect("login")

    def get(self, request):
        return self.post(request)


class VerifyEmailView(View):
    """Verify user email via token."""

    def get(self, request, token):
        try:
            verification = EmailVerification.objects.get(token=token, is_used=False)
            if verification.is_expired:
                messages.error(request, _("This verification token has expired. Please request a new one."))
            else:
                verification.is_used = True
                verification.save()
                verification.user.is_verified = True
                verification.user.save(update_fields=["is_verified"])
                messages.success(request, _("Your email has been verified successfully!"))
        except EmailVerification.DoesNotExist:
            messages.error(request, _("Invalid or expired verification link."))

        return redirect("home")


class ProfileView(LoginRequiredMixin, View):
    """View and edit user profile."""

    def get(self, request):
        form = UserProfileForm(instance=request.user.profile)
        return render(request, "accounts/profile.html", {"form": form})

    def post(self, request):
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Your profile has been updated."))
            return redirect("profile")
        return render(request, "accounts/profile.html", {"form": form})


class PasswordChangeView(LoginRequiredMixin, View):
    """Change current user password."""

    def get(self, request):
        form = PasswordChangeCustomForm(user=request.user)
        return render(request, "accounts/password_change.html", {"form": form})

    def post(self, request):
        form = PasswordChangeCustomForm(user=request.user, data=request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data["new_password"])
            request.user.save()
            # Keep user logged in after password change
            login(request, request.user)
            messages.success(request, _("Your password has been changed successfully."))
            return redirect("profile")
        return render(request, "accounts/password_change.html", {"form": form})

