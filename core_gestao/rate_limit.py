"""Rate limiting simples por IP (cache Django)."""
from django.core.cache import cache
from django.http import JsonResponse


def rate_limit_ip(request, key_prefix: str, limit: int = 15, period: int = 3600) -> bool:
    ip = (
        request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR")
        or "unknown"
    )
    key = f"rl:{key_prefix}:{ip}"
    count = cache.get(key, 0)
    if count >= limit:
        return False
    cache.set(key, count + 1, period)
    return True


def rate_limit_or_429(request, key_prefix: str, limit: int = 15, period: int = 3600):
    if rate_limit_ip(request, key_prefix, limit, period):
        return None
    return JsonResponse(
        {"success": False, "detail": "Muitas tentativas. Tente novamente mais tarde."},
        status=429,
    )
