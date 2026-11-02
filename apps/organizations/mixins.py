"""Mixins for tenant views and isolation."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse


class TenantRequiredMixin(LoginRequiredMixin):
    """
    Ensures the user is logged in and has an active tenant selected.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not getattr(request, "tenant", None):
            # If user has no organizations, redirect to organization creation
            return redirect(reverse("org_create"))

        return super().dispatch(request, *args, **kwargs)


class TenantContextMixin:
    """
    Automatically injects tenant context and scopes querysets.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(qs, "for_tenant") and getattr(self.request, "tenant", None):
            return qs.for_tenant(self.request.tenant)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tenant"] = getattr(self.request, "tenant", None)
        context["tenant_membership"] = getattr(self.request, "tenant_membership", None)
        return context

