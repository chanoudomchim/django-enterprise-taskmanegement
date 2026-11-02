"""Forms for user authentication and profile management."""

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import UserProfile

User = get_user_model()


class UserRegistrationForm(forms.ModelForm):
    """Registration form creating both a user and their initial organization."""

    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "••••••••"}),
        min_length=8,
    )
    password_confirm = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "••••••••"}),
    )
    organization_name = forms.CharField(
        label=_("Organization / Workspace Name"),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Acme Corp"}),
        help_text=_("Optional: Create your organization workspace immediately."),
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@company.com"}),
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "John"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Doe"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("password_confirm")
        if p1 and p2 and p1 != p2:
            self.add_error("password_confirm", _("Passwords do not match."))
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserLoginForm(forms.Form):
    """Authentication form using email."""

    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@company.com", "autofocus": True}),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "••••••••"}),
    )
    remember_me = forms.BooleanField(
        label=_("Remember this device for 30 days"),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            user = authenticate(email=email, password=password)
            if user is None:
                raise forms.ValidationError(_("Invalid email or password."))
            if not user.is_active:
                raise forms.ValidationError(_("This account is currently inactive."))
            cleaned_data["user"] = user
        return cleaned_data


class UserProfileForm(forms.ModelForm):
    """User personal details and preferences form."""

    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = UserProfile
        fields = ("avatar", "phone_number", "title", "bio", "timezone", "theme_preference", "language")
        widgets = {
            "avatar": forms.FileInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "timezone": forms.TextInput(attrs={"class": "form-control"}),
            "theme_preference": forms.Select(attrs={"class": "form-select"}),
            "language": forms.Select(
                choices=[("en", "English"), ("es", "Spanish"), ("fr", "French"), ("de", "German")],
                attrs={"class": "form-select"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name

    def save(self, commit=True):
        profile = super().save(commit=commit)
        user = profile.user
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        if commit:
            user.save()
        return profile


class PasswordResetRequestForm(forms.Form):
    """Request password reset link."""

    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@company.com"}),
    )


class PasswordChangeCustomForm(forms.Form):
    """Change current password."""

    old_password = forms.CharField(
        label=_("Current Password"),
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    new_password = forms.CharField(
        label=_("New Password"),
        min_length=8,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    new_password_confirm = forms.CharField(
        label=_("Confirm New Password"),
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if not self.user.check_password(old_password):
            raise forms.ValidationError(_("Current password does not match."))
        return old_password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("new_password")
        p2 = cleaned_data.get("new_password_confirm")
        if p1 and p2 and p1 != p2:
            self.add_error("new_password_confirm", _("New passwords do not match."))
        return cleaned_data

