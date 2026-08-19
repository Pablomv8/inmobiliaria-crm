from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Activity


class ActivityPaginationTests(TestCase):
    def setUp(self):
        self.agent = get_user_model().objects.create_user(
            username="activity-pagination-agent",
            password="test-password",
            role="agent",
        )
        self.client.force_login(self.agent)

    def test_activity_list_uses_its_second_page(self):
        Activity.objects.bulk_create([
            Activity(
                user=self.agent,
                action="contact_updated",
                description=f"Actividad paginada {index:02d}",
            )
            for index in range(31)
        ])

        response = self.client.get(reverse("activity_list"), {"page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(response.context["page_obj"].paginator.count, 31)
        self.assertEqual(len(response.context["activities"]), 1)
        self.assertContains(response, "Mostrando")
