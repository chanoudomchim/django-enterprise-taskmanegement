"""Context processors for organizations, multi-tenancy, and global notification counters."""


def tenant_context(request):
    """
    Exposes active tenant, user organizations, and unread notification counter to all templates.
    """
    unread_count = 0
    if getattr(request, "user", None) and request.user.is_authenticated and getattr(request, "tenant", None):
        try:
            from apps.notifications.models import Notification
            unread_count = Notification.objects.filter(
                organization=request.tenant,
                recipient=request.user,
                is_read=False,
            ).count()
        except Exception:
            unread_count = 0

    return {
        "current_organization": getattr(request, "tenant", None),
        "user_membership": getattr(request, "tenant_membership", None),
        "user_organizations": getattr(request, "user_organizations", []),
        "unread_notifications_count": unread_count,
    }
