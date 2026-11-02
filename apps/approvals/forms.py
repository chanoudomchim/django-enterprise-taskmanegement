"""Forms for Approval Workflows, Requests, and Decisions."""

from django import forms
from apps.approvals.models import ApprovalWorkflow, ApprovalRequest, ApprovalDecision
from apps.projects.models import Project
from apps.tasks.models import Task


class ApprovalRequestForm(forms.ModelForm):
    """Form to submit an approval request."""

    class Meta:
        model = ApprovalRequest
        fields = ["workflow", "title", "description", "project", "task"]
        widgets = {
            "workflow": forms.Select(attrs={"class": "form-select", "required": True}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Q3 Project Budget Approval", "required": True}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Detail the context and required approvals..."}),
            "project": forms.Select(attrs={"class": "form-select"}),
            "task": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, organization, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["workflow"].queryset = ApprovalWorkflow.objects.filter(organization=organization, is_active=True)
        self.fields["project"].queryset = Project.objects.filter(organization=organization)
        self.fields["task"].queryset = Task.objects.filter(organization=organization)
        self.fields["project"].required = False
        self.fields["task"].required = False


class ApprovalDecisionForm(forms.ModelForm):
    """Form for approvers to record approval/rejection decision."""

    class Meta:
        model = ApprovalDecision
        fields = ["decision", "comments"]
        widgets = {
            "decision": forms.Select(attrs={"class": "form-select", "required": True}),
            "comments": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional reasoning or feedback..."}),
        }


class ApprovalWorkflowForm(forms.ModelForm):
    """Form to define an approval workflow."""

    class Meta:
        model = ApprovalWorkflow
        fields = ["name", "description", "project", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Workflow Name", "required": True}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "project": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, organization, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.filter(organization=organization)
        self.fields["project"].required = False

