"""Core views for WorkFlow Enterprise."""

from django.http import JsonResponse
from django.db import connection
from django.shortcuts import render
from config.cache import is_redis_available
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Application health check endpoint for Docker and monitoring.
    Verifies database and Redis cache connectivity.
    """
    db_status = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            db_status = bool(row and row[0] == 1)
    except Exception as exc:
        logger.error("Healthcheck DB check failed: %s", exc)

    redis_status = is_redis_available()

    is_healthy = db_status
    overall_status = "healthy" if (db_status and redis_status) else ("degraded" if db_status else "unhealthy")

    data = {
        "status": overall_status,
        "services": {
            "database": "connected" if db_status else "disconnected",
            "redis_cache": "connected" if redis_status else "disconnected",
        },
        "version": "2.0",
    }

    status_code = 200 if is_healthy else 503
    return JsonResponse(data, status=status_code)


def home_view(request):
    """Temporary landing page for Phase 1."""
    return render(request, "home.html", {"title": "WorkFlow Enterprise"})

