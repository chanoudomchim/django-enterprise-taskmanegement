"""Custom DRF Authentication backends for WorkFlow Enterprise: API Client Key/Secret."""

from rest_framework import authentication, exceptions
from django.utils import timezone
from apps.integrations.models import APIClient


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    Authenticates requests using X-API-Key and X-API-Secret headers.
    Attaches authenticated APIClient's creator as request.user and organization as request.tenant.
    """

    def authenticate(self, request):
        api_key = request.headers.get("X-API-Key")
        api_secret = request.headers.get("X-API-Secret")

        if not api_key:
            return None

        client = APIClient.objects.filter(api_key=api_key, is_active=True).select_related("created_by", "organization").first()
        if not client:
            raise exceptions.AuthenticationFailed("Invalid API Key.")

        if api_secret and client.api_secret != api_secret:
            raise exceptions.AuthenticationFailed("Invalid API Secret.")

        client.last_used_at = timezone.now()
        client.save(update_fields=["last_used_at"])

        request.tenant = client.organization
        return (client.created_by, client)

