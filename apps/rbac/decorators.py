"""RBAC Permission Decorators and Mixins."""

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from apps.rbac.services import has_organization_permission


def require_tenant_permission(permission_code):
    """View decorator verifying the user holds the required tenant permission."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not getattr(request, "tenant", None):
                raise PermissionDenied(_("No active organization found."))

            if not has_organization_permission(request.user, request.tenant, permission_code):
                raise PermissionDenied(_(f"You lack the required permission: '{permission_code}'"))

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


class TenantPermissionRequiredMixin:
    """Class-based view mixin checking for tenant permission."""

    permission_required = None

    def dispatch(self, request, *args, **kwargs):
        if not self.permission_required:
            raise ValueError("permission_required attribute must be set.")

        if not getattr(request, "tenant", None):
            raise PermissionDenied(_("No active organization found."))

        if not has_organization_permission(request.user, request.tenant, self.permission_required):
            raise PermissionDenied(_(f"You lack the required permission: '{self.permission_required}'"))

        return super().dispatch(request, *args, **kwargs)

