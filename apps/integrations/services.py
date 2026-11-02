"""Services for Outgoing Webhook dispatch, HMAC signatures, and delivery retries."""

import json
import urllib.request
import logging
from django.utils import timezone
from apps.integrations.models import WebhookEndpoint, WebhookDelivery

logger = logging.getLogger(__name__)


def dispatch_webhook(endpoint, event, payload_dict):
    """
    Format, sign, and deliver a webhook payload to the endpoint URL.
    Generates an audit record in WebhookDelivery.
    """
    signature = endpoint.sign_payload(payload_dict)
    payload_bytes = json.dumps(payload_dict, sort_keys=True).encode("utf-8")

    delivery = WebhookDelivery.objects.create(
        organization=endpoint.organization,
        endpoint=endpoint,
        event=event,
        payload=payload_dict,
        status="pending",
        attempts=1,
    )

    req = urllib.request.Request(
        endpoint.url,
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "WorkFlowEnterprise-Webhook/1.0",
            "X-Webhook-Event": event,
            "X-Webhook-Signature": signature,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            delivery.status_code = response.status
            delivery.response_body = response.read()[:500].decode("utf-8", errors="ignore")
            if 200 <= response.status < 300:
                delivery.status = "sent"
                delivery.sent_at = timezone.now()
            else:
                delivery.status = "failed"
    except Exception as e:
        delivery.status = "failed"
        delivery.response_body = str(e)
        logger.warning("Webhook delivery to %s failed: %s", endpoint.url, e)

    delivery.save()
    return delivery


def trigger_event_webhooks(organization, event, payload_dict):
    """Notify all active webhook endpoints subscribed to an event."""
    endpoints = WebhookEndpoint.objects.filter(
        organization=organization,
        is_active=True,
    )
    deliveries = []
    for ep in endpoints:
        if not ep.events or event in ep.events:
            d = dispatch_webhook(ep, event, payload_dict)
            deliveries.append(d)
    return deliveries


def retry_failed_webhooks(max_attempts=3):
    """Retry deliveries that previously failed."""
    deliveries = WebhookDelivery.objects.filter(
        status="failed",
        attempts__lt=max_attempts,
    ).select_related("endpoint")

    retried = 0
    succeeded = 0
    for d in deliveries:
        retried += 1
        d.attempts += 1
        signature = d.endpoint.sign_payload(d.payload)
        payload_bytes = json.dumps(d.payload, sort_keys=True).encode("utf-8")

        req = urllib.request.Request(
            d.endpoint.url,
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "WorkFlowEnterprise-Webhook/1.0",
                "X-Webhook-Event": d.event,
                "X-Webhook-Signature": signature,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                d.status_code = response.status
                d.response_body = response.read()[:500].decode("utf-8", errors="ignore")
                if 200 <= response.status < 300:
                    d.status = "sent"
                    d.sent_at = timezone.now()
                    succeeded += 1
        except Exception as e:
            d.response_body = str(e)
        d.save()

    return retried, succeeded

