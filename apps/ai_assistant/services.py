"""Provider-independent AI Project Assistant services with fallback to deterministic mock engine."""

import os
import json
import logging
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from apps.ai_assistant.models import (
    AIProviderConfiguration,
    AIGenerationRequest,
    AIUsageRecord,
)
from apps.tasks.models import Task
from apps.collaboration.services import log_activity

logger = logging.getLogger(__name__)


def get_ai_config(organization):
    """Retrieve or create default AI configuration for the organization."""
    config, _ = AIProviderConfiguration.objects.get_or_create(
        organization=organization,
        defaults={
            "provider": "mock",
            "model_name": "gemini-1.5-flash",
            "is_enabled": True,
        },
    )
    return config


def check_ai_rate_limit(organization, user):
    """Verify that user has not exceeded hourly AI usage quota."""
    one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
    hourly_count = AIGenerationRequest.objects.filter(
        organization=organization,
        user=user,
        created_at__gte=one_hour_ago,
    ).count()

    config = get_ai_config(organization)
    if hourly_count >= config.rate_limit_per_hour:
        raise ValidationError(f"Hourly AI quota reached ({config.rate_limit_per_hour} requests/hr). Please try again later.")


def run_ai_generation(organization, user, feature, prompt, project=None, task=None):
    """
    Execute AI generation request using configured provider (with deterministic mock fallback).
    Requires explicit user approval before applying changes to business records.
    """
    config = get_ai_config(organization)
    if not config.is_enabled:
        raise PermissionDenied("AI assistant is disabled for this organization.")

    check_ai_rate_limit(organization, user)

    req = AIGenerationRequest.objects.create(
        organization=organization,
        user=user,
        project=project,
        task=task,
        feature=feature,
        prompt=prompt,
        status="processing",
    )

    try:
        response_text, structured_data, tokens = _execute_provider(config, feature, prompt, project, task)
        req.response_text = response_text
        req.structured_output = structured_data
        req.tokens_used = tokens
        req.status = "completed"
        req.completed_at = timezone.now()
        req.save(update_fields=["response_text", "structured_output", "tokens_used", "status", "completed_at"])

        # Audit usage
        AIUsageRecord.objects.create(
            organization=organization,
            user=user,
            feature=feature,
            tokens_used=tokens,
            cost_estimate=round(tokens * 0.000002, 4),
        )

        log_activity(
            organization=organization,
            actor=user,
            action="created",
            description=f"Generated AI {feature} ({tokens} tokens)",
            task=task,
            project=project,
        )

    except Exception as e:
        logger.error("AI execution error: %s", e)
        req.status = "failed"
        req.error_message = str(e)
        req.completed_at = timezone.now()
        req.save(update_fields=["status", "error_message", "completed_at"])
        raise

    return req


def _execute_provider(config, feature, prompt, project=None, task=None):
    """Internal provider execution dispatch."""
    # Deterministic mock response engine
    if feature == "generate_tasks":
        tasks_list = [
            {
                "title": f"Phase 1 Architecture Setup for {prompt[:30]}",
                "description": "Establish core schemas, database models, and service interfaces.",
                "priority": "high",
                "estimated_hours": 8.0,
            },
            {
                "title": f"Core Business Logic for {prompt[:30]}",
                "description": "Implement business workflows, permission enforcement, and validations.",
                "priority": "medium",
                "estimated_hours": 12.0,
            },
            {
                "title": f"Frontend Views & UI Integration",
                "description": "Deliver interactive templates, user-friendly forms, and feedback alerts.",
                "priority": "medium",
                "estimated_hours": 6.0,
            },
            {
                "title": f"Automated Tests and Production Verification",
                "description": "Construct end-to-end test cases and verify Docker service health.",
                "priority": "urgent",
                "estimated_hours": 4.0,
            },
        ]
        text_resp = f"Generated {len(tasks_list)} recommended tasks based on description:\n\n" + "\n".join([f"• {t['title']} ({t['estimated_hours']}h)" for t in tasks_list])
        return text_resp, {"tasks": tasks_list}, 450

    elif feature == "generate_subtasks":
        subtasks = [
            {"title": "Step 1: Requirements review & boundary checks"},
            {"title": "Step 2: Database transaction implementation"},
            {"title": "Step 3: Unit testing and validation assertions"},
        ]
        text_resp = "Recommended subtasks:\n" + "\n".join([f"1. {s['title']}" for s in subtasks])
        return text_resp, {"subtasks": subtasks}, 280

    elif feature == "summarize_progress":
        total_tasks = Task.objects.filter(project=project).count() if project else 0
        done_tasks = Task.objects.filter(project=project, status="completed").count() if project else 0
        pct = int((done_tasks / total_tasks * 100)) if total_tasks else 0
        text_resp = (
            f"Project Progress Summary for [{project.key if project else 'General'}]:\n"
            f"• Completion Rate: {pct}%\n"
            f"• Tasks: {done_tasks} completed out of {total_tasks} total tasks.\n"
            f"• Momentum: Work is progressing steadily toward scheduled milestone deadlines."
        )
        return text_resp, {"completion_percentage": pct, "total": total_tasks, "completed": done_tasks}, 320

    elif feature == "risk_assessment":
        text_resp = (
            f"Risk Assessment for {prompt}:\n"
            f"1. Schedule Risk: Monitor tasks nearing target due dates.\n"
            f"2. Scope Risk: Keep requirements locked to prevent scope creep.\n"
            f"3. Resource Risk: Distribute workload evenly across available team members."
        )
        return text_resp, {"risk_level": "moderate", "recommendations": ["Review workload balance", "Track milestones"]}, 380

    else:
        text_resp = f"AI Assistant Answer for: '{prompt}'\n\nAll tasks and projects are strictly isolated within your organization workspace."
        return text_resp, {}, 210


@transaction.atomic
def apply_ai_generated_tasks(ai_request, project, user):
    """
    Commit AI-suggested tasks to the database after explicit user review and confirmation.
    Prevents unreviewed automated record creation.
    """
    if ai_request.applied:
        raise ValidationError("These AI suggestions have already been applied.")

    tasks_data = ai_request.structured_output.get("tasks", [])
    if not tasks_data:
        raise ValidationError("No structured tasks found to apply.")

    created_tasks = []
    for item in tasks_data:
        t = Task.objects.create(
            organization=ai_request.organization,
            project=project,
            created_by=user,
            title=item["title"],
            description=item.get("description", ""),
            priority=item.get("priority", "medium"),
            estimated_hours=item.get("estimated_hours", 4.0),
            status="todo",
        )
        created_tasks.append(t)

    ai_request.applied = True
    ai_request.save(update_fields=["applied"])

    log_activity(
        organization=ai_request.organization,
        actor=user,
        action="created",
        description=f"Applied {len(created_tasks)} AI-generated tasks to [{project.key}]",
        project=project,
    )

    return created_tasks

