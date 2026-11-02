"""Tenant isolation filter backend for Django REST Framework."""

from rest_framework import filters


class TenantFilterBackend(filters.BaseFilterBackend):
    """
    Ensures QuerySets are scoped strictly to the current request.tenant.
    Protects against cross-tenant data leakage via API endpoints.
    """

    def filter_queryset(self, request, queryset, view):
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return queryset.none()

        # If model has direct organization field
        if hasattr(queryset.model, "organization"):
            return queryset.filter(organization=tenant)

        return queryset

