"""Audit logging helper service."""

from apps.audit.models import AuditLog


def get_client_ip(request):
    """Safely extract remote client IP address from HTTP request headers."""
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def record_audit_log(
    organization,
    user,
    action,
    model_name,
    object_id="",
    object_repr="",
    changes=None,
    request=None,
):
    """Create an immutable AuditLog entry."""
    ip = get_client_ip(request)
    ua = request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""

    return AuditLog.objects.create(
        organization=organization,
        user=user if user and user.is_authenticated else None,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        object_repr=str(object_repr)[:255],
        changes=changes or {},
        ip_address=ip,
        user_agent=ua,
    )

