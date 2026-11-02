"""Forms for Organization management."""

from django import forms
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import Organization, OrganizationSettings, OrganizationInvitation, OrganizationMembership


class OrganizationCreateForm(forms.ModelForm):
    """Create a new tenant organization."""

    class Meta:
        model = Organization
        fields = ("name", "logo", "primary_color")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Acme Innovations"}),
            "logo": forms.FileInput(attrs={"class": "form-control"}),
            "primary_color": forms.TextInput(attrs={"type": "color", "class": "form-control form-control-color"}),
        }


class OrganizationSettingsForm(forms.ModelForm):
    """Update settings and feature toggles."""

    class Meta:
        model = OrganizationSettings
        fields = (
            "allow_member_invites",
            "default_role",
            "timezone",
            "default_language",
            "time_tracking_enabled",
            "ai_assistant_enabled",
            "telegram_notifications_enabled",
        )
        widgets = {
            "allow_member_invites": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "default_role": forms.Select(attrs={"class": "form-select"}),
            "timezone": forms.TextInput(attrs={"class": "form-control"}),
            "default_language": forms.Select(
                choices=[("en", "English"), ("es", "Spanish"), ("fr", "French")],
                attrs={"class": "form-select"},
            ),
            "time_tracking_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "ai_assistant_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "telegram_notifications_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class OrganizationInviteForm(forms.ModelForm):
    """Invite a new user to the organization."""

    class Meta:
        model = OrganizationInvitation
        fields = ("email", "role")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "colleague@company.com"}),
            "role": forms.Select(attrs={"class": "form-select"}),
        }

