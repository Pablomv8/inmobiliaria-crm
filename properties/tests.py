from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from contacts.models import Contact

from .forms import OwnerContactForm, PropertyForm
from .models import Property, Zone


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
        for property_type in ("flat", "local", "solar", "terreno"):
            with self.subTest(property_type=property_type):
                form = PropertyForm(data={
                    "street": "Calle Mayor",
                    "number": "10",
                    "city": "Madrid",
                    "property_type": property_type,
                    "status": "prospect",
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

        response = self.client.post(
            reverse("property_create"),
            {
                "street": "Calle Nueva",
                "number": "12",
                "city": "Madrid",
                "zone": self.second_zone.pk,
                "property_type": "local",
                "status": "prospect",
            },
        )

        created_property = Property.objects.get(street="Calle Nueva")
        self.assertRedirects(response, reverse("properties"))
        self.assertEqual(created_property.zone, self.second_zone)

    def test_edit_form_changes_property_zone(self):
        response = self.client.post(
            reverse("property_update", args=[self.property.pk]),
            {
                "street": self.property.street,
                "number": self.property.number,
                "city": self.property.city,
                "zone": self.second_zone.pk,
                "property_type": self.property.property_type,
                "status": self.property.status,
            },
        )

        self.property.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("property_detail", args=[self.property.pk]),
        )
        self.assertEqual(self.property.zone, self.second_zone)


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
