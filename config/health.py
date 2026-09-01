from pathlib import Path

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def live(request):
    return JsonResponse({"status": "ok"})


@never_cache
@require_GET
def ready(request):
    checks = {"database": False, "media": False}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["database"] = cursor.fetchone()[0] == 1
    except Exception:
        checks["database"] = False

    media_root = Path(settings.MEDIA_ROOT)
    checks["media"] = media_root.exists() and media_root.is_dir()
    healthy = all(checks.values())
    return JsonResponse(
        {"status": "ok" if healthy else "unavailable", "checks": checks},
        status=200 if healthy else 503,
    )
