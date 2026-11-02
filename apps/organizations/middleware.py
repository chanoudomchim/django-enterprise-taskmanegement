"""Multi-tenant isolation middleware."""

from apps.organizations.models import Organization, OrganizationMembership


class TenantMiddleware:
    """
    Middleware that identifies the active tenant (Organization) for the authenticated user
    and securely attaches it to the request object as `request.tenant`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        request.tenant_membership = None
        request.user_organizations = []

        if getattr(request, "user", None) and request.user.is_authenticated:
            # Query all active memberships for this user
            memberships = list(
                OrganizationMembership.objects.filter(
                    user=request.user,
                    is_active=True,
                    organization__is_active=True,
                ).select_related("organization")
            )
            request.user_organizations = [m.organization for m in memberships]

            # 1. Check API header X-Organization-ID or session active_organization_id
            header_org_id = request.headers.get("X-Organization-ID")
            session_org_id = request.session.get("active_organization_id")
            target_org_id = header_org_id or session_org_id

            active_membership = None
            if target_org_id:
                for m in memberships:
                    if str(m.organization_id) == str(target_org_id):
                        active_membership = m
                        break

            # 2. If no target or invalid target, fallback to default or first active membership
            if not active_membership and memberships:
                for m in memberships:
                    if m.is_default:
                        active_membership = m
                        break
                if not active_membership:
                    active_membership = memberships[0]

            if active_membership:
                request.tenant = active_membership.organization
                request.tenant_membership = active_membership
                # Keep session updated if not an API request with custom header
                if not header_org_id:
                    request.session["active_organization_id"] = str(active_membership.organization_id)

        response = self.get_response(request)
        return response

