"""Forms for Collaboration: Comments and Attachments."""

from django import forms
from apps.collaboration.models import Comment, Attachment


class CommentForm(forms.ModelForm):
    """Form to submit or edit a discussion comment."""

    class Meta:
        model = Comment
        fields = ["content", "is_internal"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Write a comment or internal note... (use @email to mention team members)",
                    "required": True,
                }
            ),
            "is_internal": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }


class AttachmentForm(forms.ModelForm):
    """Form to upload a file attachment."""

    class Meta:
        model = Attachment
        fields = ["file", "is_public"]
        widgets = {
            "file": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "required": True,
                }
            ),
            "is_public": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

