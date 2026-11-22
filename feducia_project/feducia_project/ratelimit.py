from functools import wraps

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse

LIMIT_MESSAGE = "Too many attempts. Please try again later."


def rate_limit(scope, limit, window, as_json=False):
    """Обмежує кількість POST-запитів з однієї IP-адреси за window секунд."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method == "POST":
                key = f"ratelimit_{scope}_{request.META.get('REMOTE_ADDR')}"
                cache.add(key, 0, timeout=window)

                try:
                    attempts = cache.incr(key)
                except ValueError:
                    # Ключ встиг протухнути між add та incr
                    cache.set(key, 1, timeout=window)
                    attempts = 1

                if attempts > limit:
                    if as_json:
                        return JsonResponse({"status": "error", "message": LIMIT_MESSAGE}, status=429)
                    return HttpResponse(LIMIT_MESSAGE, status=429)

            return view(request, *args, **kwargs)
        return wrapper
    return decorator
