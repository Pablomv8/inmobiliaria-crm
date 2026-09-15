from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse


class SecurityHeaderTests(SimpleTestCase):
    def test_referrer_policy_allows_cross_origin_map_identification(self):
        self.assertEqual(
            settings.SECURE_REFERRER_POLICY,
            "strict-origin-when-cross-origin",
        )

        response = self.client.get(reverse("health_live"))

        self.assertEqual(
            response.headers["Referrer-Policy"],
            "strict-origin-when-cross-origin",
        )
