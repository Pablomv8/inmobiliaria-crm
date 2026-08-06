from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from properties.models import Property

from .models import News, NewsComment


class NewsCrudTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="agent",
            password="test-password",
        )
        self.property = Property.objects.create(
            street="Calle Mayor",
            number="10",
            city="Madrid",
            property_type="local",
        )
        self.client.force_login(self.user)

    def create_news(self):
        return News.objects.create(
            related_property=self.property,
            agent=self.user,
            motivation="sale",
            client_price="250000",
            estimated_price="240000",
            status="new",
        )

    def test_news_list_is_available_from_its_own_route(self):
        response = self.client.get(reverse("news_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Noticias")
        self.assertContains(response, reverse("news_create_general"))

    def test_create_news_from_general_form(self):
        response = self.client.post(
            reverse("news_create_general"),
            {
                "related_property": self.property.pk,
                "motivation": "rent",
                "client_price": "180000",
                "estimated_price": "175000",
                "status": "contacted",
            },
        )

        news = News.objects.get()
        self.assertRedirects(response, reverse("news_detail", args=[news.pk]))
        self.assertEqual(news.related_property, self.property)
        self.assertEqual(news.agent, self.user)

    def test_create_news_from_property(self):
        response = self.client.post(
            reverse("news_create", args=[self.property.pk]),
            {
                "motivation": "sale",
                "client_price": "250000",
                "estimated_price": "240000",
                "status": "new",
            },
        )

        news = News.objects.get()
        self.assertRedirects(response, reverse("news_detail", args=[news.pk]))
        self.assertEqual(news.related_property, self.property)

    def test_creating_news_activates_property_from_any_previous_status(self):
        for index, previous_status in enumerate(
            ["reserved", "sold", "rented", "prospect"],
            start=1,
        ):
            with self.subTest(previous_status=previous_status):
                property_obj = Property.objects.create(
                    street="Calle Reactivación",
                    number=str(index),
                    city="Madrid",
                    property_type="flat",
                    status=previous_status,
                )

                News.objects.create(
                    related_property=property_obj,
                    agent=self.user,
                    motivation="sale",
                    client_price="250000",
                    estimated_price="240000",
                )

                property_obj.refresh_from_db()
                self.assertEqual(property_obj.status, "active")

    def test_update_news(self):
        news = self.create_news()

        response = self.client.post(
            reverse("news_update", args=[news.pk]),
            {
                "related_property": self.property.pk,
                "motivation": "rent",
                "client_price": "260000",
                "estimated_price": "255000",
                "status": "follow_up",
            },
        )

        news.refresh_from_db()
        self.assertRedirects(response, reverse("news_detail", args=[news.pk]))
        self.assertEqual(news.motivation, "rent")
        self.assertEqual(news.status, "new")

    def test_add_comment_records_its_author(self):
        news = self.create_news()

        response = self.client.post(
            reverse("news_add_comment", args=[news.pk]),
            {"text": "El propietario confirma disponibilidad."},
        )

        comment = NewsComment.objects.get()
        self.assertRedirects(response, reverse("news_detail", args=[news.pk]))
        self.assertEqual(comment.user, self.user)
        news.refresh_from_db()
        self.assertEqual(news.status, "contacted")

    def test_delete_news(self):
        news = self.create_news()

        response = self.client.post(reverse("news_delete", args=[news.pk]))

        self.assertRedirects(response, reverse("news_list"))
        self.assertFalse(News.objects.filter(pk=news.pk).exists())
