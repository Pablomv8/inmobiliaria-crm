from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import Listing
from news.models import News
from orders.models import Order
from properties.models import Property, Zone

from .forms import ContactForm
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
            is_owner=True,
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
            is_buyer=True,
            assigned_agent=self.agent,
        )
        zone = Zone.objects.create(name="Centro contacto")
        order = Order.objects.create(
            buyer=buyer,
            operation_type="sale",
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

    def test_contact_list_shows_roles_column(self):
        Contact.objects.create(
            name="Propietario del listado",
            phone="600555111",
            is_owner=True,
            assigned_agent=self.agent,
        )
        Contact.objects.create(
            name="Compradora del listado",
            phone="600555222",
            is_buyer=True,
            assigned_agent=self.agent,
        )

        response = self.client.get(reverse("contact_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Roles")

    def test_contact_with_both_roles_shows_owner_and_buyer_sections(self):
        contact = Contact.objects.create(
            name="Cliente con doble rol",
            phone="600555223",
            is_owner=True,
            is_buyer=True,
            assigned_agent=self.agent,
        )

        response = self.client.get(reverse("contact_detail", args=[contact.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Propietario y comprador")
        self.assertContains(response, "Noticias relacionadas")
        self.assertContains(response, "Encargos relacionados")
        self.assertContains(response, "Pedidos de búsqueda")

    def test_contact_list_is_paginated_and_keeps_filters(self):
        for index in range(17):
            Contact.objects.create(
                name=f"Comprador paginado {index:02d}",
                phone=f"611000{index:03d}",
                is_buyer=True,
                assigned_agent=self.agent,
            )
        Contact.objects.create(
            name="Propietario fuera del filtro",
            phone="622000000",
            is_owner=True,
            assigned_agent=self.agent,
        )

        response = self.client.get(
            reverse("contact_list"),
            {"role": "buyer", "page": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(response.context["page_obj"].paginator.count, 17)
        self.assertEqual(len(response.context["contacts"]), 2)
        self.assertContains(response, "role=buyer")
        self.assertContains(response, "Mostrando")
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
            is_owner=True,
        )
        self.client.force_login(manager)

        response = self.client.get(reverse("contact_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, contact.name)
        self.assertContains(response, "Sin asignar")

    def test_administrator_can_assign_a_contact_to_themself(self):
        administrator = get_user_model().objects.create_user(
            username="contact-administrator",
            password="test-password",
            role="admin",
        )
        contact = Contact.objects.create(
            name="Contacto del administrador",
            phone="600555334",
            is_owner=True,
        )
        self.client.force_login(administrator)

        response = self.client.post(
            reverse("contact_assign_agent", args=[contact.pk]),
            {"agent_id": administrator.pk},
        )

        contact.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(contact.assigned_agent, administrator)

    def test_agent_sees_all_contacts_and_can_filter_by_responsible(self):
        other_agent = get_user_model().objects.create_user(
            username="contact-other-agent",
            password="test-password",
            role="agent",
        )
        own_contact = Contact.objects.create(
            name="Contacto propio visible",
            phone="600555401",
            is_buyer=True,
            assigned_agent=self.agent,
        )
        other_contact = Contact.objects.create(
            name="Contacto de otro agente visible",
            phone="600555402",
            is_owner=True,
            assigned_agent=other_agent,
        )
        unassigned_contact = Contact.objects.create(
            name="Contacto sin responsable visible",
            phone="600555403",
            is_owner=True,
        )

        response = self.client.get(reverse("contact_list"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(own_contact, response.context["contacts"])
        self.assertIn(other_contact, response.context["contacts"])
        self.assertIn(unassigned_contact, response.context["contacts"])
        self.assertContains(response, "Todos los responsables")

        filtered_response = self.client.get(
            reverse("contact_list"),
            {"agent": other_agent.pk},
        )
        self.assertQuerySetEqual(
            filtered_response.context["contacts"],
            [other_contact],
        )

    def test_contact_list_can_filter_by_role(self):
        owner = Contact.objects.create(
            name="Propietario filtrado",
            phone="600666111",
            is_owner=True,
            assigned_agent=self.agent,
        )
        buyer = Contact.objects.create(
            name="Comprador excluido",
            phone="600666222",
            is_buyer=True,
            assigned_agent=self.agent,
        )

        response = self.client.get(
            reverse("contact_list"),
            {"role": "owner"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["contacts"], [owner])
        self.assertContains(response, "Propietarios")
        self.assertContains(response, owner.name)
        self.assertNotContains(response, buyer.name)

    def test_contact_list_can_filter_contacts_with_both_roles(self):
        both = Contact.objects.create(
            name="Cliente con ambos roles filtrado",
            phone="600666333",
            is_owner=True,
            is_buyer=True,
            assigned_agent=self.agent,
        )
        Contact.objects.create(
            name="Solo comprador fuera",
            phone="600666444",
            is_buyer=True,
            assigned_agent=self.agent,
        )

        response = self.client.get(
            reverse("contact_list"),
            {"role": "both"},
        )

        self.assertQuerySetEqual(response.context["contacts"], [both])
        self.assertContains(response, "Ambos roles")

    def test_contact_search_includes_document_and_city(self):
        matching_contact = Contact.objects.create(
            name="Contacto encontrado",
            phone="600777111",
            identification_number="12345678Z",
            city="Alcalá de Henares",
            is_buyer=True,
            assigned_agent=self.agent,
        )
        Contact.objects.create(
            name="Contacto diferente",
            phone="600777222",
            identification_number="87654321X",
            city="Toledo",
            is_buyer=True,
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
        self.assertContains(response, "data-required-marker")
        for field_name in (
            "last_name",
            "identification_number",
            "marital_status",
            "phone",
        ):
            self.assertTrue(response.context["form"].fields[field_name].required)
        self.assertNotIn("assigned_agent", response.context["form"].fields)

    def test_contact_form_validates_and_normalizes_common_personal_data(self):
        form = ContactForm(data={
            "name": "Cliente validado",
            "last_name": "García Pérez",
            "phone": "612 345 678",
            "email": "CLIENTE@EXAMPLE.COM",
            "postal_code": "11630",
            "identification_number": "12345678-z",
            "marital_status": "single",
            "is_buyer": "on",
            "assigned_agent": self.agent.pk,
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["phone"], "+34612345678")
        self.assertEqual(form.cleaned_data["email"], "cliente@example.com")
        self.assertEqual(form.cleaned_data["identification_number"], "12345678Z")

    def test_contact_form_accepts_owner_and_buyer_roles_together(self):
        form = ContactForm(data={
            "name": "Cliente doble",
            "last_name": "Rol Válido",
            "phone": "612 345 679",
            "identification_number": "87654321X",
            "marital_status": "single",
            "is_owner": "on",
            "is_buyer": "on",
            "assigned_agent": self.agent.pk,
        })

        self.assertTrue(form.is_valid(), form.errors)
        contact = form.save()
        self.assertTrue(contact.is_owner)
        self.assertTrue(contact.is_buyer)

    def test_buyer_only_cannot_receive_properties_from_contact_form(self):
        form = ContactForm(data={
            "name": "Comprador sin inmueble",
            "last_name": "Formulario Seguro",
            "phone": "612 345 681",
            "identification_number": "12345678Z",
            "marital_status": "single",
            "is_buyer": "on",
            "properties": [self.property.pk],
            "assigned_agent": self.agent.pk,
        })

        self.assertTrue(form.is_valid(), form.errors)
        contact = form.save()
        self.assertFalse(contact.properties.exists())

    def test_editing_buyer_only_preserves_historical_property_relations(self):
        buyer = Contact.objects.create(
            name="Comprador histórico",
            last_name="Con relación",
            phone="+34612345682",
            identification_number="87654321X",
            marital_status="single",
            is_buyer=True,
            assigned_agent=self.agent,
        )
        buyer.properties.add(self.property)
        form = ContactForm(data={
            "name": buyer.name,
            "last_name": buyer.last_name,
            "phone": "612 345 682",
            "identification_number": buyer.identification_number,
            "marital_status": buyer.marital_status,
            "is_buyer": "on",
            "assigned_agent": self.agent.pk,
        }, instance=buyer)

        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertTrue(buyer.properties.filter(pk=self.property.pk).exists())

    def test_contact_form_hides_properties_until_owner_role_is_selected(self):
        response = self.client.get(reverse("contact_create"))

        self.assertContains(
            response,
            'id="contact-properties-field" class="md:col-span-2 hidden"',
            html=False,
        )
        self.assertContains(response, "updatePropertiesVisibility")

    def test_contact_form_requires_at_least_one_role(self):
        form = ContactForm(data={
            "name": "Cliente sin rol",
            "last_name": "No válido",
            "phone": "612 345 680",
            "identification_number": "X1234567L",
            "marital_status": "single",
            "assigned_agent": self.agent.pk,
        })

        self.assertFalse(form.is_valid())
        self.assertIn("Selecciona al menos un rol", form.non_field_errors()[0])

    def test_contact_form_rejects_invalid_email_phone_document_and_postal_code(self):
        form = ContactForm(data={
            "name": "Cliente no válido",
            "phone": "12345",
            "email": "correo-sin-formato",
            "postal_code": "99000",
            "identification_number": "12345678A",
            "is_owner": "on",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)
        self.assertIn("email", form.errors)
        self.assertIn("postal_code", form.errors)
        self.assertIn("identification_number", form.errors)
        self.assertIn("last_name", form.errors)
        self.assertIn("marital_status", form.errors)
