"""URL patterns for AI Project Assistant."""

from django.urls import path
from apps.ai_assistant.views import (
    AIAssistantConsoleView,
    AIGenerateView,
    AIRequestDetailView,
    AIApplyTasksView,
)

urlpatterns = [
    path("ai/", AIAssistantConsoleView.as_view(), name="ai_console"),
    path("ai/generate/", AIGenerateView.as_view(), name="ai_generate"),
    path("ai/requests/<uuid:request_id>/", AIRequestDetailView.as_view(), name="ai_request_detail"),
    path("ai/requests/<uuid:request_id>/apply/", AIApplyTasksView.as_view(), name="ai_apply_tasks"),
]

