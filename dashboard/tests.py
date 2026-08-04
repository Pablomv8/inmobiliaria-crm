from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from calendar_app.models import Appointment
from contacts.models import Contact
from listings.models import Listing
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
