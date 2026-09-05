import json
from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase
from django.urls import reverse
from PIL import Image


class PwaTests(SimpleTestCase):
    def test_manifest_is_public_and_installable(self):
        response = self.client.get(reverse("pwa_manifest"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/manifest+json",
        )
        manifest = response.json()
        self.assertEqual(manifest["name"], "InmoCRM · Gestión inmobiliaria")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["scope"], "/")
        self.assertEqual(
            {icon["sizes"] for icon in manifest["icons"]},
            {"192x192", "512x512"},
        )
        self.assertTrue(
            any(icon.get("purpose") == "maskable" for icon in manifest["icons"])
        )

    def test_service_worker_has_root_scope_and_safe_cache_policy(self):
        response = self.client.get(reverse("pwa_service_worker"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("application/javascript"))
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        self.assertContains(response, "request.mode === 'navigate'")
        self.assertContains(response, "fetch(request).catch")
        self.assertContains(response, "url.pathname.startsWith('/static/')")
        body = response.content.decode()
        self.assertLess(
            body.index("request.mode === 'navigate'"),
            body.index("url.pathname.startsWith('/static/')"),
        )
        self.assertLess(
            body.index("url.pathname.startsWith('/static/')"),
            body.index("cache.put(request, copy)"),
        )

    def test_offline_page_is_public_and_explains_data_policy(self):
        response = self.client.get(reverse("pwa_offline"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sin conexión")
        self.assertContains(response, "los datos de clientes e inmuebles no se almacenan")

    def test_base_registers_worker_and_exposes_install_ui(self):
        source = get_template("base.html").template.source
        navbar = get_template("partials/navbar.html").template.source

        self.assertIn('rel="manifest"', source)
        self.assertIn("navigator.serviceWorker.register", source)
        self.assertIn("beforeinstallprompt", source)
        self.assertIn("data-pwa-install", navbar)

    def test_required_icon_dimensions(self):
        icon_dir = Path(settings.BASE_DIR) / "static" / "pwa"
        expected = {
            "apple-touch-icon.png": (180, 180),
            "icon-192.png": (192, 192),
            "icon-512.png": (512, 512),
            "icon-maskable-512.png": (512, 512),
        }

        for filename, size in expected.items():
            with self.subTest(filename=filename):
                with Image.open(icon_dir / filename) as image:
                    self.assertEqual(image.size, size)
                    self.assertEqual(image.format, "PNG")
