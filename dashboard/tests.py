from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from calendar_app.models import Appointment
from contacts.models import Contact
from listings.models import Listing
from news.models import News
from orders.models import Order
from properties.models import Property


class DashboardScopeTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.agent = user_model.objects.create_user(
            username="dashboard-agent",
            password="test-password",
            role="agent",
        )
        self.other_agent = user_model.objects.create_user(
            username="dashboard-other",
            password="test-password",
            role="agent",
        )
        self.manager = user_model.objects.create_user(
            username="dashboard-manager",
            password="test-password",
            role="manager",
        )
        self.agent_owner = Contact.objects.create(
            name="Propietaria dashboard",
            phone="600400001",
            contact_type="owner",
            assigned_agent=self.agent,
        )
        self.agent_buyer = Contact.objects.create(
            name="Compradora dashboard",
            phone="600400002",
            contact_type="buyer",
            assigned_agent=self.agent,
        )
        self.other_buyer = Contact.objects.create(
            name="Comprador de otro agente",
            phone="600400003",
            contact_type="buyer",
            assigned_agent=self.other_agent,
        )
        self.agent_property = Property.objects.create(
            street="Calle Dashboard",
            number="1",
            city="Madrid",
            property_type="flat",
        )
        other_property = Property.objects.create(
            street="Calle Dashboard",
            number="2",
            city="Madrid",
            property_type="house",
        )
        self.agent_listing = Listing.objects.create(
            property=self.agent_property,
            listing_type="sale",
            owner_price="200000",
            agency_price="210000",
            price_diference="10000",
            owner=self.agent_owner,
            agent=self.agent,
        )
        Listing.objects.create(
            property=other_property,
            listing_type="sale",
            owner_price="250000",
            agency_price="260000",
            price_diference="10000",
            agent=self.other_agent,
        )
        Order.objects.create(
            buyer=self.agent_buyer,
            max_price="230000",
            payment_type="financing",
            property_type="flat",
        )
        Order.objects.create(
            buyer=self.other_buyer,
            max_price="280000",
            payment_type="cash",
            property_type="house",
        )
        Appointment.objects.create(
            related_property=self.agent_property,
            contact=self.agent_buyer,
            agent=self.agent,
            appointment_type="sale",
            date=date(2026, 8, 20),
            time=time(10, 0),
            listing=self.agent_listing,
        )
        News.objects.create(
            related_property=self.agent_property,
            agent=self.agent,
            motivation="sale",
            client_price="210000",
            estimated_price="205000",
        )
        News.objects.create(
            related_property=other_property,
            agent=self.other_agent,
            motivation="sale",
            client_price="260000",
            estimated_price="255000",
        )

    def test_agent_only_sees_personal_portfolio(self):
        self.client.force_login(self.agent)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["my_listings"], 1)
        self.assertEqual(response.context["my_active_listings"], 1)
        self.assertEqual(response.context["my_orders"], 1)
        self.assertEqual(response.context["my_contacts"], 2)
        self.assertEqual(response.context["my_scheduled_appointments"], 1)
        self.assertFalse(response.context["is_office_viewer"])
        self.assertNotIn("office_listings", response.context)
        self.assertContains(response, "Mi cartera")
        self.assertNotContains(response, "Vista global de la oficina")

    def test_manager_sees_office_totals_and_every_user(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_office_viewer"])
        self.assertEqual(response.context["office_listings"], 2)
        self.assertEqual(response.context["office_active_listings"], 2)
        self.assertEqual(response.context["office_orders"], 2)
        self.assertEqual(response.context["office_contacts"], 3)
        self.assertEqual(len(response.context["user_rows"]), 3)
        self.assertContains(response, "Vista global de la oficina")
        self.assertContains(response, "dashboard-agent")
        self.assertContains(response, "dashboard-other")

    def test_personal_cards_link_to_logged_user_filters(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("dashboard"))
        html = response.content.decode()

        self.assertIn(
            f"{reverse('listing_list')}?agent={self.manager.pk}",
            html,
        )
        self.assertIn(
            f"{reverse('order_list')}?agent={self.manager.pk}",
            html,
        )
        self.assertIn(
            f"{reverse('news_list')}?agent={self.manager.pk}",
            html,
        )
        self.assertIn(
            f"{reverse('calendar')}?agents={self.manager.pk}",
            html,
        )

    def test_manager_can_filter_lists_by_user_from_global_view(self):
        self.client.force_login(self.manager)

        orders_response = self.client.get(
            reverse("order_list"),
            {"agent": self.agent.pk},
        )
        self.assertEqual(len(orders_response.context["orders"]), 1)
        self.assertEqual(
            orders_response.context["orders"][0].buyer,
            self.agent_buyer,
        )

        news_response = self.client.get(
            reverse("news_list"),
            {"agent": self.agent.pk},
        )
        self.assertEqual(len(news_response.context["news_items"]), 1)
        self.assertEqual(news_response.context["news_items"][0].agent, self.agent)

        contacts_response = self.client.get(
            reverse("contact_list"),
            {"agent": self.agent.pk},
        )
        self.assertEqual(len(contacts_response.context["contacts"]), 2)

        calendar_response = self.client.get(
            reverse("calendar"),
            {"agents": self.agent.pk},
        )
        self.assertEqual(
            calendar_response.context["selected_agent_ids"],
            [str(self.agent.pk)],
        )

    def test_agent_cannot_use_filter_to_see_another_agents_orders(self):
        self.client.force_login(self.agent)
        response = self.client.get(
            reverse("order_list"),
            {"agent": self.other_agent.pk},
        )

        self.assertEqual(len(response.context["orders"]), 1)
        self.assertEqual(response.context["orders"][0].buyer, self.agent_buyer)

    def test_manager_sees_worker_tracking_cards_with_assigned_metrics(self):
        inactive_agent = get_user_model().objects.create_user(
            username="inactive-agent",
            password="test-password",
            role="agent",
            is_active=False,
        )
        self.client.force_login(self.manager)

        response = self.client.get(reverse("team_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["worker_count"], 2)
        workers = [row["user"] for row in response.context["worker_rows"]]
        self.assertIn(self.agent, workers)
        self.assertIn(self.other_agent, workers)
        self.assertNotIn(self.manager, workers)
        self.assertNotIn(inactive_agent, workers)
        agent_row = next(
            row for row in response.context["worker_rows"]
            if row["user"] == self.agent
        )
        self.assertEqual(agent_row["contacts"], 2)
        self.assertEqual(agent_row["news"], 1)
        self.assertEqual(agent_row["listings"], 1)
        self.assertEqual(agent_row["orders"], 1)
        self.assertEqual(agent_row["scheduled_appointments"], 1)
        self.assertContains(
            response,
            reverse("team_member_detail", args=[self.agent.pk]),
        )

    def test_manager_sees_selected_worker_detail_and_recent_portfolio(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("team_member_detail", args=[self.agent.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["worker"], self.agent)
        self.assertEqual(response.context["contacts_total"], 2)
        self.assertEqual(response.context["owners_total"], 1)
        self.assertEqual(response.context["buyers_total"], 1)
        self.assertEqual(response.context["news_total"], 1)
        self.assertEqual(response.context["listings_total"], 1)
        self.assertEqual(response.context["orders_total"], 1)
        self.assertEqual(response.context["scheduled_appointments"], 1)
        self.assertContains(response, "Indicadores de seguimiento")
        self.assertContains(response, self.agent_property.full_address)
        self.assertContains(
            response,
            f"{reverse('contact_list')}?agent={self.agent.pk}",
        )

    def test_agent_cannot_access_team_tracking(self):
        self.client.force_login(self.agent)

        overview_response = self.client.get(reverse("team_overview"))
        detail_response = self.client.get(
            reverse("team_member_detail", args=[self.other_agent.pk])
        )

        self.assertEqual(overview_response.status_code, 403)
        self.assertEqual(detail_response.status_code, 403)

    def test_only_active_agents_have_a_tracking_detail(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("team_member_detail", args=[self.manager.pk])
        )

        self.assertEqual(response.status_code, 404)
