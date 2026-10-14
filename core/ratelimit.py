from django.core.cache import cache


def allow(key, limit=60, window=60):
    """Fixed-window rate limiter backed by the Django cache."""
    cache_key = f'rl:{key}'
    if cache.add(cache_key, 1, window):
        return True
    try:
        count = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, window)
        return True
    return count <= limit
