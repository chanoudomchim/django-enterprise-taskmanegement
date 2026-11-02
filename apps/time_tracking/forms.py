"""Forms for Time Tracking: Manual logging, Timers, and Timesheet Review."""

from django import forms
from django.utils import timezone
from apps.time_tracking.models import TimeEntry, ActiveTimer
from apps.projects.models import Project
from apps.tasks.models import Task


class ManualTimeEntryForm(forms.ModelForm):
    """Form to manually record work hours."""

    hours = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0.1,
        max_value=24.0,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 2.5", "step": "0.25", "required": True}),
        help_text="Duration in hours (e.g., 1.5)",
    )

    class Meta:
        model = TimeEntry
        fields = ["project", "task", "date", "description", "is_billable", "hourly_rate"]
        widgets = {
            "project": forms.Select(attrs={"class": "form-select", "required": True}),
            "task": forms.Select(attrs={"class": "form-select"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date", "required": True}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Describe work performed..."}),
            "is_billable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "hourly_rate": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Optional billable rate"}),
        }

    def __init__(self, organization, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.filter(organization=organization)
        self.fields["task"].queryset = Task.objects.filter(organization=organization)
        self.fields["task"].required = False
        if not self.initial.get("date"):
            self.initial["date"] = timezone.localdate()
        self.fields["is_billable"].initial = True


class ActiveTimerStartForm(forms.Form):
    """Form to start a live active timer."""

    project = forms.ModelChoiceField(
        queryset=Project.objects.none(),
        widget=forms.Select(attrs={"class": "form-select", "required": True}),
    )
    task = forms.ModelChoiceField(
        queryset=Task.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "What are you working on?"}),
    )
    is_billable = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, organization, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.filter(organization=organization)
        self.fields["task"].queryset = Task.objects.filter(organization=organization)


class TimesheetReviewForm(forms.Form):
    """Form for manager to approve or reject a timesheet."""

    action = forms.ChoiceField(
        choices=[("approved", "Approve Timesheet"), ("rejected", "Reject Timesheet")],
        widget=forms.Select(attrs={"class": "form-select", "required": True}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Reasoning or feedback..."}),
    )
