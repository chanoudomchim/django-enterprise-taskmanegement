"""WorkFlow Enterprise - Cache Utilities and Helpers."""

from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def tenant_cache_key(org_id, key_name):
    """Generate an organization-scoped cache key to prevent cross-tenant cache contamination."""
    return f"tenant:{org_id}:{key_name}"


def get_tenant_cache(org_id, key_name, default=None):
    """Retrieve an organization-scoped cached item."""
    k = tenant_cache_key(org_id, key_name)
    return cache.get(k, default)


def set_tenant_cache(org_id, key_name, value, timeout=300):
    """Store an organization-scoped item in Redis."""
    k = tenant_cache_key(org_id, key_name)
    return cache.set(k, value, timeout=timeout)


def delete_tenant_cache(org_id, key_name):
    """Invalidate an organization-scoped cache entry."""
    k = tenant_cache_key(org_id, key_name)
    return cache.delete(k)


def is_redis_available():
    """Check connectivity to Redis cache."""
    try:
        cache.set("_health_check_ping", "pong", 10)
        return cache.get("_health_check_ping") == "pong"
    except Exception as e:
        logger.warning("Redis cache connectivity check failed: %s", e)
        return False

