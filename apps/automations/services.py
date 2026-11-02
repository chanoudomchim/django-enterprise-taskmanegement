"""Services for evaluating and executing automation rules and trigger actions."""

import logging
from django.db import transaction
from apps.automations.models import AutomationRule, AutomationAction, AutomationExecution
from apps.notifications.services import send_notification
from apps.integrations.services import trigger_event_webhooks

logger = logging.getLogger(__name__)


@transaction.atomic
def execute_automation_rule(rule, context):
    """
    Evaluate rule conditions against event context and execute child actions.
    Records an AutomationExecution log.
    """
    conditions = rule.conditions or {}

    # Check matching conditions (e.g. status matches target)
    for key, expected_val in conditions.items():
        if context.get(key) != expected_val:
            return None

    results = []
    task = context.get("task")
    project = context.get("project")

    for action in rule.actions.all().order_by("order"):
        p = action.parameters or {}
        try:
            if action.action_type == "change_status" and task:
                new_status = p.get("new_status")
                if new_status:
                    task.status = new_status
                    task.save(update_fields=["status", "updated_at"])
                    results.append(f"Changed status to '{new_status}'")

            elif action.action_type == "send_notification":
                recipient = context.get("user") or (task.created_by if task else None)
                if recipient:
                    send_notification(
                        recipient=recipient,
                        organization=rule.organization,
                        title=p.get("title", f"Automation: {rule.name}"),
                        body=p.get("body", "An automated action was triggered."),
                        task=task,
                        project=project,
                    )
                    results.append("Sent notification")

            elif action.action_type == "trigger_webhook":
                event_name = p.get("event", f"automation.{rule.trigger}")
                trigger_event_webhooks(
                    organization=rule.organization,
                    event=event_name,
                    payload_dict={
                        "rule": rule.name,
                        "task_key": task.task_key if task else None,
                        "status": task.status if task else None,
                    },
                )
                results.append("Triggered webhook")

        except Exception as e:
            logger.error("Failed executing action %s: %s", action, e)
            results.append(f"Error: {e}")

    execution = AutomationExecution.objects.create(
        organization=rule.organization,
        rule=rule,
        status="success",
        result={"actions_executed": results},
    )
    return execution


def fire_automation_trigger(organization, trigger_type, context):
    """Scan and execute active rules matching the trigger."""
    rules = AutomationRule.objects.filter(
        organization=organization,
        trigger=trigger_type,
        is_active=True,
    ).prefetch_related("actions")

    executions = []
    for r in rules:
        ex = execute_automation_rule(r, context)
        if ex:
            executions.append(ex)
    return executions

