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
        self.new_agent = get_user_model().objects.create_user(
            username="news-new-agent",
            password="test-password",
        )
        self.manager = get_user_model().objects.create_user(
            username="news-manager",
            password="test-password",
            role="manager",
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

    def test_news_list_and_detail_show_the_assigned_agent(self):
        news = self.create_news()

        list_response = self.client.get(reverse("news_list"))
        detail_response = self.client.get(
            reverse("news_detail", args=[news.pk])
        )

        self.assertContains(list_response, "Agente asignado")
        self.assertContains(list_response, self.user.username)
        self.assertContains(detail_response, "Agente asignado")
        self.assertContains(detail_response, self.user.username)

    def test_news_without_agent_is_shown_as_unassigned(self):
        news = News.objects.create(
            related_property=self.property,
            agent=None,
            motivation="sale",
            client_price="250000",
            estimated_price="240000",
            status="new",
        )
        self.client.force_login(self.manager)

        list_response = self.client.get(reverse("news_list"))
        detail_response = self.client.get(
            reverse("news_detail", args=[news.pk])
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(list_response, "Sin asignar")
        self.assertContains(detail_response, "Sin asignar")

    def test_news_list_can_be_ordered_by_property_address(self):
        self.create_news()
        other_property = Property.objects.create(
            street="Avenida Abad",
            number="2",
            city="Madrid",
            property_type="flat",
        )
        other_news = News.objects.create(
            related_property=other_property,
            agent=self.user,
            motivation="sale",
            client_price="200000",
            estimated_price="195000",
        )

        response = self.client.get(reverse("news_list"), {"ordering": "address"})

        self.assertEqual(response.context["news_items"][0], other_news)
        self.assertContains(response, 'option value="address" selected', html=False)

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

    def test_creating_news_sets_news_status_from_any_non_terminal_context(self):
        for index, occupied_by in enumerate(
            ["owner", "vacant"],
            start=1,
        ):
            with self.subTest(occupied_by=occupied_by):
                property_obj = Property.objects.create(
                    street="Calle Reactivación",
                    number=str(index),
                    city="Madrid",
                    property_type="flat",
                    occupied_by=occupied_by,
                )

                News.objects.create(
                    related_property=property_obj,
                    agent=self.user,
                    motivation="sale",
                    client_price="250000",
                    estimated_price="240000",
                )

                property_obj.refresh_from_db()
                self.assertEqual(property_obj.status, "news")

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

    def test_manager_can_reassign_news(self):
        news = self.create_news()
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("news_update", args=[news.pk]),
            {
                "related_property": self.property.pk,
                "agent": self.new_agent.pk,
                "motivation": "sale",
                "client_price": "250000",
                "estimated_price": "240000",
            },
        )

        news.refresh_from_db()
        self.assertRedirects(response, reverse("news_detail", args=[news.pk]))
        self.assertEqual(news.agent, self.new_agent)

    def test_administrator_can_assign_news_to_themself(self):
        administrator = get_user_model().objects.create_user(
            username="news-administrator",
            password="test-password",
            role="admin",
        )
        self.client.force_login(administrator)

        response = self.client.post(
            reverse("news_create_general"),
            {
                "related_property": self.property.pk,
                "agent": administrator.pk,
                "motivation": "sale",
                "client_price": "250000",
                "estimated_price": "240000",
            },
        )

        news = News.objects.get()
        self.assertRedirects(response, reverse("news_detail", args=[news.pk]))
        self.assertEqual(news.agent, administrator)

    def test_agent_cannot_reassign_news_through_post_data(self):
        news = self.create_news()

        self.client.post(
            reverse("news_update", args=[news.pk]),
            {
                "related_property": self.property.pk,
                "agent": self.new_agent.pk,
                "motivation": "sale",
                "client_price": "250000",
                "estimated_price": "240000",
            },
        )

        news.refresh_from_db()
        self.assertEqual(news.agent, self.user)

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
