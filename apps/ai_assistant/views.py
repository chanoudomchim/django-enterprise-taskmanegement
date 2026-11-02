"""Views for AI Project Assistant Console, Generation, and Task Confirmation."""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.translation import gettext_lazy as _
from apps.organizations.mixins import TenantRequiredMixin
from apps.ai_assistant.models import AIGenerationRequest, AIProviderConfiguration
from apps.ai_assistant.forms import AIGenerationForm
from apps.ai_assistant.services import (
    run_ai_generation,
    apply_ai_generated_tasks,
    get_ai_config,
)


class AIAssistantConsoleView(TenantRequiredMixin, View):
    """Interactive AI Assistant dashboard, prompt submitter, and job history."""

    def get(self, request):
        config = get_ai_config(request.tenant)
        recent_requests = (
            AIGenerationRequest.objects.filter(organization=request.tenant, user=request.user)
            .select_related("project")
            .order_by("-created_at")[:15]
        )
        form = AIGenerationForm(organization=request.tenant)

        return render(
            request,
            "ai_assistant/console.html",
            {
                "config": config,
                "recent_requests": recent_requests,
                "form": form,
            },
        )


class AIGenerateView(TenantRequiredMixin, View):
    """Process an AI generation request."""

    def post(self, request):
        form = AIGenerationForm(request.tenant, request.POST)
        if form.is_valid():
            feature = form.cleaned_data["feature"]
            prompt = form.cleaned_data["prompt"]
            project = form.cleaned_data.get("project")

            try:
                ai_req = run_ai_generation(
                    organization=request.tenant,
                    user=request.user,
                    feature=feature,
                    prompt=prompt,
                    project=project,
                )
                messages.success(request, _(f"AI assistant completed request ({ai_req.tokens_used} tokens)."))
                return redirect("ai_request_detail", request_id=ai_req.id)
            except (ValidationError, PermissionDenied) as e:
                messages.error(request, str(e.message if hasattr(e, "message") else e))
            except Exception as e:
                messages.error(request, _(f"AI generation failed: {e}"))
        else:
            messages.error(request, _("Please fill in required prompt and feature fields."))

        return redirect("ai_console")


class AIRequestDetailView(TenantRequiredMixin, View):
    """Inspect AI output, review structured tasks, and confirm application."""

    def get(self, request, request_id):
        ai_req = get_object_or_404(
            AIGenerationRequest.objects.select_related("project", "task"),
            organization=request.tenant,
            id=request_id,
        )
        tasks_list = ai_req.structured_output.get("tasks", [])

        return render(
            request,
            "ai_assistant/request_detail.html",
            {
                "ai_req": ai_req,
                "tasks_list": tasks_list,
            },
        )


class AIApplyTasksView(TenantRequiredMixin, View):
    """User approval action: commits AI suggested tasks to the project database."""

    def post(self, request, request_id):
        ai_req = get_object_or_404(
            AIGenerationRequest,
            organization=request.tenant,
            id=request_id,
        )
        if not ai_req.project:
            messages.error(request, _("Cannot apply tasks without an associated project."))
            return redirect("ai_request_detail", request_id=ai_req.id)

        try:
            created = apply_ai_generated_tasks(ai_req, ai_req.project, request.user)
            messages.success(request, _(f"Successfully added {len(created)} tasks to [{ai_req.project.key}]."))
            return redirect("project_detail", project_key=ai_req.project.key)
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, "message") else e))
            return redirect("ai_request_detail", request_id=ai_req.id)

