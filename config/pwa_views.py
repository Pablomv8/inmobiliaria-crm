import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import cache_control, never_cache


@cache_control(public=True, max_age=3600)
def manifest(request):
    """Serve the install metadata with storage-aware static asset URLs."""
    data = {
        "id": "/",
        "name": "InmoCRM · Gestión inmobiliaria",
        "short_name": "InmoCRM",
        "description": (
            "Gestión de inmuebles, personas, noticias, encargos, pedidos "
            "y agenda comercial."
        ),
        "lang": "es-ES",
        "dir": "ltr",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "display_override": ["window-controls-overlay", "standalone"],
        "orientation": "any",
        "background_color": "#f3f4f6",
        "theme_color": "#111827",
        "categories": ["business", "productivity"],
        "icons": [
            {
                "src": static("pwa/icon-192.png"),
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": static("pwa/icon-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": static("pwa/icon-maskable-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
        "shortcuts": [
            {
                "name": "Mi jornada",
                "short_name": "Jornada",
                "url": reverse("daily_work"),
                "icons": [
                    {
                        "src": static("pwa/icon-192.png"),
                        "sizes": "192x192",
                    }
                ],
            },
            {
                "name": "Agenda",
                "short_name": "Agenda",
                "url": reverse("calendar"),
                "icons": [
                    {
                        "src": static("pwa/icon-192.png"),
                        "sizes": "192x192",
                    }
                ],
            },
            {
                "name": "Tareas",
                "short_name": "Tareas",
                "url": reverse("task_list"),
                "icons": [
                    {
                        "src": static("pwa/icon-192.png"),
                        "sizes": "192x192",
                    }
                ],
            },
        ],
    }
    response = JsonResponse(
        data,
        json_dumps_params={"ensure_ascii": False},
    )
    response["Content-Type"] = "application/manifest+json"
    return response


@never_cache
def service_worker(request):
    """Serve the worker at the site root so its scope covers the CRM."""
    core_assets = [
        reverse("pwa_offline"),
        static("pwa/icon-192.png"),
        static("pwa/icon-512.png"),
        static("pwa/icon-maskable-512.png"),
    ]
    response = render(
        request,
        "pwa/service_worker.js",
        {
            "pwa_cache_version": settings.PWA_CACHE_VERSION,
            "pwa_core_assets_json": json.dumps(core_assets),
        },
        content_type="application/javascript",
    )
    response["Service-Worker-Allowed"] = "/"
    return response


@cache_control(public=True, max_age=86400)
def offline(request):
    return render(request, "pwa/offline.html")
