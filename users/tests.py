from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthenticationLayoutTests(TestCase):
    def test_logout_page_does_not_render_authenticated_navigation(self):
        user = get_user_model().objects.create_user(
            username="logout-layout-user",
            password="test-password",
            role="agent",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("logout"), follow=True)

        self.assertRedirects(response, reverse("login"))
        self.assertContains(response, "Iniciar sesión")
        self.assertNotContains(response, "Cerrar sesión")
        self.assertNotContains(response, "Dashboard")
