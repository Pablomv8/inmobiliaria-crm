from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from contacts.models import Contact
from calendar_app.models import Appointment
from listings.models import Listing
from news.models import News
from sales.models import Sale

from .forms import OwnerContactForm, PropertyForm
from .models import Property, PropertyComment, PropertyStatusHistory, Zone


class PropertyModelTests(TestCase):

    def test_property_only_uses_supported_types(self):
        self.assertEqual(
            Property.PROPERTY_TYPE_CHOICES,
            (
                ("flat", "Piso"),
                ("house", "Casa"),
                ("villa", "Villa"),
                ("office", "Oficina"),
                ("local", "Local"),
                ("nave", "Nave"),
                ("solar", "Solar"),
                ("terreno", "Terreno"),
            ),
        )

    def test_property_no_longer_has_title_or_price_fields(self):
        field_names = {field.name for field in Property._meta.get_fields()}

        self.assertNotIn("title", field_names)
        self.assertNotIn("price", field_names)

    def test_property_form_no_longer_exposes_title_or_price(self):
        form = PropertyForm()

        self.assertNotIn("title", form.fields)
        self.assertNotIn("price", form.fields)
        self.assertNotIn("status", form.fields)
        self.assertIn("occupied_by", form.fields)

    def test_property_form_exposes_zone_ordered_by_name(self):
        second_zone = Zone.objects.create(name="Zona Sur")
        first_zone = Zone.objects.create(name="Zona Centro")

        form = PropertyForm()

        self.assertIn("zone", form.fields)
        self.assertEqual(
            list(form.fields["zone"].queryset),
            [first_zone, second_zone],
        )
        self.assertEqual(
            form.fields["zone"].empty_label,
            "Selecciona una zona",
        )

    def test_property_form_accepts_previous_and_new_types(self):
        for property_type in ("flat", "local", "nave", "solar", "terreno"):
            with self.subTest(property_type=property_type):
                form = PropertyForm(data={
                    "street": "Calle Mayor",
                    "number": "10",
                    "city": "Madrid",
                    "property_type": property_type,
                    "occupied_by": "owner",
                })

                self.assertTrue(form.is_valid(), form.errors)


class PropertyFormViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="property-form-user",
            password="test-password",
            role="agent",
        )
        self.first_zone = Zone.objects.create(name="Centro inmueble")
        self.second_zone = Zone.objects.create(name="Norte inmueble")
        self.property = Property.objects.create(
            street="Calle Antigua",
            number="5",
            city="Madrid",
            property_type="flat",
            zone=self.first_zone,
        )
        self.client.force_login(self.user)

    def test_create_form_displays_and_saves_zone(self):
        form_response = self.client.get(reverse("property_create"))

        self.assertEqual(form_response.status_code, 200)
        self.assertContains(form_response, "1. Ubicación y clasificación")
        self.assertContains(form_response, 'name="zone"', html=False)
        self.assertContains(form_response, 'name="occupied_by"', html=False)
        self.assertNotContains(form_response, 'name="status"', html=False)

        response = self.client.post(
            reverse("property_create"),
            {
                "street": "Calle Nueva",
                "number": "12",
                "city": "Madrid",
                "zone": self.second_zone.pk,
                "property_type": "local",
                "occupied_by": "vacant",
            },
        )

        created_property = Property.objects.get(street="Calle Nueva")
        self.assertRedirects(response, reverse("properties"))
        self.assertEqual(created_property.zone, self.second_zone)
        self.assertEqual(created_property.occupied_by, "vacant")
        self.assertEqual(created_property.status, "vacant")

    def test_edit_form_changes_property_zone(self):
        response = self.client.post(
            reverse("property_update", args=[self.property.pk]),
            {
                "street": self.property.street,
                "number": self.property.number,
                "city": self.property.city,
                "zone": self.second_zone.pk,
                "property_type": self.property.property_type,
                "occupied_by": "tenants",
            },
        )

        self.property.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("property_detail", args=[self.property.pk]),
        )
        self.assertEqual(self.property.zone, self.second_zone)
        self.assertEqual(self.property.occupied_by, "tenants")
        self.assertEqual(self.property.status, "rented")


class PropertyAutomaticStatusTests(TestCase):
    def setUp(self):
        self.agent = get_user_model().objects.create_user(
            username="property-status-agent",
            password="test-password",
            role="agent",
        )
        self.property = Property.objects.create(
            street="Calle Estados",
            number="1",
            city="Madrid",
            property_type="flat",
            occupied_by="owner",
        )
        self.owner = Contact.objects.create(
            name="Propietaria estados",
            phone="600111222",
            contact_type="owner",
        )
        self.buyer = Contact.objects.create(
            name="Comprador estados",
            phone="600333444",
            contact_type="buyer",
        )
        self.client.force_login(self.agent)

    def test_new_property_starts_as_never_contacted(self):
        self.assertEqual(self.property.status, "never_contacted")

    def test_occupancy_sets_vacant_or_rented_status(self):
        vacant = Property.objects.create(
            street="Calle Vacía",
            number="2",
            city="Madrid",
            property_type="house",
            occupied_by="vacant",
        )
        rented = Property.objects.create(
            street="Calle Alquilada",
            number="3",
            city="Madrid",
            property_type="flat",
            occupied_by="tenants",
        )

        self.assertEqual(vacant.status, "vacant")
        self.assertEqual(rented.status, "rented")

    def test_property_comment_marks_contact_and_records_author(self):
        response = self.client.post(
            reverse("property_add_comment", args=[self.property.pk]),
            {"text": "La propietaria pide que volvamos a llamar."},
        )

        comment = PropertyComment.objects.get()
        self.property.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("property_detail", args=[self.property.pk]),
        )
        self.assertEqual(comment.user, self.agent)
        self.assertEqual(self.property.status, "contacted")
        detail_response = self.client.get(
            reverse("property_detail", args=[self.property.pk])
        )
        self.assertContains(detail_response, "Historial de contacto")
        self.assertContains(
            detail_response,
            "La propietaria pide que volvamos a llamar.",
        )
        history = PropertyStatusHistory.objects.get()
        self.assertEqual(history.old_status, "never_contacted")
        self.assertEqual(history.new_status, "contacted")

    def test_detail_timeline_combines_creation_contact_status_and_appointment(self):
        PropertyComment.objects.create(
            property=self.property,
            user=self.agent,
            text="Se realiza el primer contacto.",
        )
        Appointment.objects.create(
            related_property=self.property,
            contact=self.owner,
            agent=self.agent,
            appointment_type="valuation",
            date=date(2026, 8, 20),
            time=time(10, 0),
            end_time=time(11, 0),
        )

        response = self.client.get(
            reverse("property_detail", args=[self.property.pk])
        )
        event_types = {event["type"] for event in response.context["timeline"]}

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            {"creation", "comment", "status", "appointment"}.issubset(
                event_types
            )
        )
        self.assertContains(response, "Timeline del inmueble")
        self.assertContains(response, "Cita de Valoración")
        self.assertContains(response, "10:00–11:00")

    def test_property_owner_links_to_contact_detail(self):
        self.owner.properties.add(self.property)

        response = self.client.get(
            reverse("property_detail", args=[self.property.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'href="{reverse("contact_detail", args=[self.owner.pk])}"',
        )
        self.assertContains(response, self.owner.name)

    def test_contact_older_than_30_days_is_refreshed_automatically(self):
        comment = PropertyComment.objects.create(
            property=self.property,
            user=self.agent,
            text="Contacto antiguo.",
        )
        PropertyComment.objects.filter(pk=comment.pk).update(
            created_at=timezone.now() - timedelta(days=31),
        )

        self.client.get(reverse("properties"))

        self.property.refresh_from_db()
        self.assertEqual(self.property.status, "contacted_30")

    def test_new_comment_reactivates_an_old_contact(self):
        comment = PropertyComment.objects.create(
            property=self.property,
            user=self.agent,
            text="Contacto antiguo.",
        )
        PropertyComment.objects.filter(pk=comment.pk).update(
            created_at=timezone.now() - timedelta(days=31),
        )
        self.property.sync_status()
        self.assertEqual(self.property.status, "contacted_30")

        PropertyComment.objects.create(
            property=self.property,
            user=self.agent,
            text="Nuevo contacto.",
        )

        self.property.refresh_from_db()
        self.assertEqual(self.property.status, "contacted")

    def test_news_and_listing_take_priority_over_contact(self):
        PropertyComment.objects.create(
            property=self.property,
            user=self.agent,
            text="Primer contacto.",
        )
        news = News.objects.create(
            related_property=self.property,
            agent=self.agent,
            motivation="sale",
            client_price="250000",
            estimated_price="240000",
        )
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, "news")

        listing = Listing.objects.create(
            property=self.property,
            owner=self.owner,
            listing_type="sale",
            owner_price="245000",
            agency_price="250000",
            agreed_price="248000",
            price_diference="5000",
            agent=self.agent,
        )
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, "in_listing")

        listing.status = "cancelled"
        listing.save()
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, "news")

        news.delete()
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, "contacted")

    def test_signed_sale_marks_property_as_sold(self):
        Sale.objects.create(
            related_property=self.property,
            buyer=self.buyer,
            agent=self.agent,
            sale_price="250000",
            commission_amount="7500",
            sale_date=timezone.localdate(),
            status="signed",
        )

        self.property.refresh_from_db()
        self.assertEqual(self.property.status, "sold")


class OwnerContactFormTests(TestCase):
    def setUp(self):
        self.agent = get_user_model().objects.create_user(
            username="owner-form-agent",
            password="test-password",
            role="agent",
        )
        self.property = Property.objects.create(
            street="Calle del Formulario",
            number="8",
            city="Madrid",
            property_type="flat",
        )
        self.client.force_login(self.agent)

    def test_owner_form_uses_spanish_labels_and_hides_fixed_fields(self):
        form = OwnerContactForm(property_obj=self.property)

        self.assertEqual(form.fields["name"].label, "Nombre")
        self.assertEqual(form.fields["last_name"].label, "Apellidos")
        self.assertEqual(form.fields["assigned_agent"].label, "Agente asignado")
        self.assertEqual(form.fields["marital_status"].choices[0][1], "Selecciona el estado civil")
        self.assertNotIn("contact_type", form.fields)
        self.assertNotIn("properties", form.fields)

    def test_owner_form_view_is_grouped_into_visual_sections(self):
        response = self.client.get(
            reverse("create_owner_for_property", args=[self.property.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Información personal")
        self.assertContains(response, "Datos de contacto")
        self.assertContains(response, "Domicilio del propietario")
        self.assertContains(response, "Gestión comercial")
        self.assertContains(response, "Notas internas")

    def test_creating_owner_keeps_automatic_property_relationship(self):
        response = self.client.post(
            reverse("create_owner_for_property", args=[self.property.pk]),
            {
                "name": "María",
                "last_name": "García",
                "phone": "612345678",
                "email": "maria@example.com",
                "assigned_agent": self.agent.pk,
            },
        )

        owner = Contact.objects.get(name="María")
        self.assertRedirects(
            response,
            reverse("property_detail", args=[self.property.pk]),
        )
        self.assertEqual(owner.contact_type, "owner")
        self.assertEqual(owner.assigned_agent, self.agent)
        self.assertTrue(owner.properties.filter(pk=self.property.pk).exists())
