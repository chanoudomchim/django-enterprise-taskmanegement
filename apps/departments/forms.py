"""Forms for Departments and Teams."""

from django import forms
from django.contrib.auth import get_user_model
from apps.departments.models import Department, Team

User = get_user_model()


class DepartmentForm(forms.ModelForm):
    """Department creation and edit form."""

    class Meta:
        model = Department
        fields = ("name", "code", "description", "manager")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Engineering"}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. ENG"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "manager": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, organization, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only allow members of the active organization as managers
        self.fields["manager"].queryset = User.objects.filter(
            organization_memberships__organization=organization,
            organization_memberships__is_active=True,
        )


class TeamForm(forms.ModelForm):
    """Team creation and edit form."""

    class Meta:
        model = Team
        fields = ("department", "name", "description", "lead")
        widgets = {
            "department": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Frontend Core"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "lead": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, organization, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(organization=organization, is_active=True)
        self.fields["lead"].queryset = User.objects.filter(
            organization_memberships__organization=organization,
            organization_memberships__is_active=True,
        )

