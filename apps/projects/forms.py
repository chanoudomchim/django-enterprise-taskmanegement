"""Forms for Projects."""

from django import forms
from django.contrib.auth import get_user_model
from apps.projects.models import Project, ProjectMilestone

User = get_user_model()


class ProjectForm(forms.ModelForm):
    """Project creation and edit form."""

    class Meta:
        model = Project
        fields = (
            "name",
            "key",
            "description",
            "status",
            "priority",
            "manager",
            "budget",
            "start_date",
            "target_end_date",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Website Redesign"}),
            "key": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. WEB", "maxlength": "8"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "manager": forms.Select(attrs={"class": "form-select"}),
            "budget": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "target_end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, organization, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["manager"].queryset = User.objects.filter(
            organization_memberships__organization=organization,
            organization_memberships__is_active=True,
        )


class ProjectMilestoneForm(forms.ModelForm):
    """Milestone creation form."""

    class Meta:
        model = ProjectMilestone
        fields = ("title", "description", "due_date", "status")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Phase 1 Release"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

