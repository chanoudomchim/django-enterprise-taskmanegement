"""Forms for Notification Preferences and Telegram Configuration."""

from django import forms
from apps.notifications.models import NotificationPreference, TelegramIntegration


class NotificationPreferenceForm(forms.ModelForm):
    """Form to manage notification channels and subscriptions."""

    class Meta:
        model = NotificationPreference
        fields = [
            "in_app_notifications",
            "email_notifications",
            "telegram_notifications",
            "notify_on_task_assigned",
            "notify_on_comment_mention",
            "notify_on_due_date",
            "notify_on_approvals",
            "daily_summary_enabled",
            "weekly_summary_enabled",
        ]
        widgets = {
            "in_app_notifications": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "email_notifications": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "telegram_notifications": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notify_on_task_assigned": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notify_on_comment_mention": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notify_on_due_date": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notify_on_approvals": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "daily_summary_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "weekly_summary_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TelegramIntegrationForm(forms.ModelForm):
    """Form for organization admin to configure Telegram bot token."""

    class Meta:
        model = TelegramIntegration
        fields = ["bot_name", "bot_token", "is_enabled"]
        widgets = {
            "bot_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. MyOrgWorkFlowBot"}),
            "bot_token": forms.PasswordInput(attrs={"class": "form-control", "placeholder": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"}),
            "is_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

