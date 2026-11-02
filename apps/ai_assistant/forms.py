"""Forms for AI Project Assistant."""

from django import forms
from apps.ai_assistant.models import AIGenerationRequest
from apps.projects.models import Project


class AIGenerationForm(forms.Form):
    """Form to submit an AI generation query or command."""

    feature = forms.ChoiceField(
        choices=AIGenerationRequest.FEATURE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select", "required": True}),
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Optional project context",
    )
    prompt = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Describe what you want the AI assistant to do (e.g. Generate task breakdown for Mobile App V2, or assess project risks)...",
                "required": True,
            }
        ),
    )

    def __init__(self, organization, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.filter(organization=organization)

