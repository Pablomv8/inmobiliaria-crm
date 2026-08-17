from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import Listing
from news.models import News
from orders.models import Order
from properties.models import Property, Zone

from .models import Contact


class ContactRelatedWorkflowTests(TestCase):
    def setUp(self):
        self.agent = get_user_model().objects.create_user(
            username="contact-workflow-agent",
            password="test-password",
            role="agent",
        )
        self.property = Property.objects.create(
            street="Calle Contacto",
            number="12",
            city="Madrid",
            property_type="flat",
        )
        self.client.force_login(self.agent)

    def test_owner_detail_lists_related_news_and_listings(self):
        owner = Contact.objects.create(
            name="Propietaria relacionada",
            phone="600111222",
            contact_type="owner",
            assigned_agent=self.agent,
        )
        owner.properties.add(self.property)
        news = News.objects.create(
            related_property=self.property,
            agent=self.agent,
            motivation="sale",
            client_price="250000",
            estimated_price="245000",
        )
        listing = Listing.objects.create(
            property=self.property,
            owner=owner,
            listing_type="sale",
            owner_price="250000",
            agency_price="245000",
            agreed_price="247500",
            price_diference="5000",
            agent=self.agent,
        )

        response = self.client.get(reverse("contact_detail", args=[owner.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["news_items"], [news])
        self.assertQuerySetEqual(response.context["listings"], [listing])
        self.assertContains(response, "Noticias relacionadas")
        self.assertContains(response, "Encargos relacionados")
        self.assertContains(response, reverse("news_detail", args=[news.pk]))
        self.assertContains(
            response,
            reverse("listing_detail", args=[listing.pk]),
        )

    def test_buyer_detail_lists_assigned_orders(self):
        buyer = Contact.objects.create(
            name="Compradora relacionada",
            phone="600333444",
            contact_type="buyer",
            assigned_agent=self.agent,
        )
        zone = Zone.objects.create(name="Centro contacto")
        order = Order.objects.create(
            buyer=buyer,
            zone=zone,
            max_price="275000",
            payment_type="financing",
            property_type="flat",
        )

        response = self.client.get(reverse("contact_detail", args=[buyer.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["orders"], [order])
        self.assertContains(response, "Pedidos de búsqueda")
        self.assertContains(response, reverse("order_detail", args=[order.pk]))
        self.assertNotContains(response, "Noticias relacionadas")
        self.assertNotContains(response, "Encargos relacionados")

    def test_contact_list_shows_contact_type_column(self):
        Contact.objects.create(
            name="Propietario del listado",
            phone="600555111",
            contact_type="owner",
            assigned_agent=self.agent,
        )
        Contact.objects.create(
            name="Compradora del listado",
            phone="600555222",
            contact_type="buyer",
            assigned_agent=self.agent,
        )

        response = self.client.get(reverse("contact_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tipo de contacto")
        self.assertContains(response, "Propietario")
        self.assertContains(response, "Comprador")

    def test_manager_can_list_a_contact_without_assigned_agent(self):
        manager = get_user_model().objects.create_user(
            username="contact-list-manager",
            password="test-password",
            role="manager",
        )
        contact = Contact.objects.create(
            name="Contacto sin responsable",
            phone="600555333",
            contact_type="owner",
        )
        self.client.force_login(manager)

        response = self.client.get(reverse("contact_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, contact.name)
        self.assertContains(response, "Sin asignar")

    def test_contact_list_can_filter_by_contact_type(self):
        owner = Contact.objects.create(
            name="Propietario filtrado",
            phone="600666111",
            contact_type="owner",
            assigned_agent=self.agent,
        )
        buyer = Contact.objects.create(
            name="Comprador excluido",
            phone="600666222",
            contact_type="buyer",
            assigned_agent=self.agent,
        )

        response = self.client.get(
            reverse("contact_list"),
            {"contact_type": "owner"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["contacts"], [owner])
        self.assertContains(response, "Propietarios")
        self.assertContains(response, owner.name)
        self.assertNotContains(response, buyer.name)

    def test_contact_search_includes_document_and_city(self):
        matching_contact = Contact.objects.create(
            name="Contacto encontrado",
            phone="600777111",
            identification_number="12345678Z",
            city="Alcalá de Henares",
            contact_type="buyer",
            assigned_agent=self.agent,
        )
        Contact.objects.create(
            name="Contacto diferente",
            phone="600777222",
            identification_number="87654321X",
            city="Toledo",
            contact_type="buyer",
            assigned_agent=self.agent,
        )

        document_response = self.client.get(
            reverse("contact_list"),
            {"search": "12345678Z"},
        )
        city_response = self.client.get(
            reverse("contact_list"),
            {"search": "Alcalá"},
        )

        self.assertQuerySetEqual(
            document_response.context["contacts"],
            [matching_contact],
        )
        self.assertQuerySetEqual(
            city_response.context["contacts"],
            [matching_contact],
        )

    def test_contact_form_uses_the_grouped_recent_style(self):
        response = self.client.get(reverse("contact_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1. Información personal")
        self.assertContains(response, "2. Datos de contacto")
        self.assertContains(response, "3. Gestión comercial")
        self.assertContains(response, "4. Información adicional")
        self.assertContains(response, "rounded-3xl")
