"""Forms for Task management."""

from django import forms
from django.contrib.auth import get_user_model
from apps.tasks.models import Task, TaskCategory, TaskLabel, TaskChecklist, TaskChecklistItem
from apps.projects.models import Project

User = get_user_model()


class TaskForm(forms.ModelForm):
    """Task creation and editing form."""

    assignees = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "3"}),
    )

    class Meta:
        model = Task
        fields = (
            "project",
            "title",
            "description",
            "status",
            "priority",
            "category",
            "labels",
            "start_date",
            "due_date",
            "estimated_hours",
            "parent_task",
        )
        widgets = {
            "project": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Task summary or action item"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "labels": forms.SelectMultiple(attrs={"class": "form-select", "size": "3"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "estimated_hours": forms.NumberInput(attrs={"class": "form-control", "step": "0.25"}),
            "parent_task": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, organization, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.filter(organization=organization)
        self.fields["category"].queryset = TaskCategory.objects.filter(organization=organization)
        self.fields["labels"].queryset = TaskLabel.objects.filter(organization=organization)
        self.fields["parent_task"].queryset = Task.objects.filter(organization=organization)
        self.fields["assignees"].queryset = User.objects.filter(
            organization_memberships__organization=organization,
            organization_memberships__is_active=True,
        )

        if self.instance and self.instance.pk:
            self.fields["assignees"].initial = [a.user for a in self.instance.assignments.all()]


class TaskChecklistForm(forms.ModelForm):
    """Checklist container creation form."""

    class Meta:
        model = TaskChecklist
        fields = ("title",)
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Checklist Name"}),
        }


class TaskChecklistItemForm(forms.ModelForm):
    """Individual checklist item form."""

    class Meta:
        model = TaskChecklistItem
        fields = ("content",)
        widgets = {
            "content": forms.TextInput(attrs={"class": "form-control", "placeholder": "Add an action item..."}),
        }

