from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from contacts.models import Contact
from calendar_app.models import Appointment
from listings.models import Listing
from news.models import News
from sales.models import Sale
from tasks.models import Street

from .forms import OwnerContactForm, PropertyForm
from .geocoding import GeocodingResult, geocode_address
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
        self.assertIn("block", form.fields)
        self.assertIn("floor", form.fields)
        self.assertIn("door", form.fields)

    def test_flat_full_address_includes_block_floor_and_door(self):
        property_obj = Property(
            street="Calle Corredera",
            number="12",
            city="Arcos de la Frontera",
            property_type="flat",
            block="B",
            floor="2º",
            door="A",
        )

        self.assertEqual(
            property_obj.full_address,
            "Calle Corredera 12, Bloque/portal B, Planta 2º, Puerta A, "
            "Arcos de la Frontera",
        )

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

    def test_new_property_form_defaults_to_arcos_and_cadiz(self):
        form = PropertyForm()

        self.assertEqual(form["city"].value(), "Arcos de la Frontera")
        self.assertEqual(form["province"].value(), "Cádiz")
        self.assertTrue(form.fields["latitude"].widget.is_hidden)
        self.assertTrue(form.fields["longitude"].widget.is_hidden)

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
        self.suggested_street = Street.objects.create(
            name="Calle Corredera",
            municipality="Arcos de la Frontera",
        )
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
        self.assertContains(form_response, "property-location-map")
        self.assertContains(form_response, "Comprobar ubicación")
        self.assertContains(form_response, "address-suggestions")
        self.assertContains(form_response, reverse("property_address_suggestions"))
        self.assertContains(form_response, "address-block-field")
        self.assertContains(form_response, "updateAddressFields")
        self.assertContains(form_response, "/static/leaflet.js")

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
        self.assertEqual(created_property.created_by, self.user)

    def test_flat_address_details_are_saved(self):
        response = self.client.post(
            reverse("property_create"),
            {
                "street": "Calle Corredera",
                "number": "12",
                "block": "B",
                "floor": "2º",
                "door": "A",
                "city": "Madrid",
                "zone": self.second_zone.pk,
                "property_type": "flat",
                "occupied_by": "owner",
            },
        )

        self.assertRedirects(response, reverse("properties"))
        property_obj = Property.objects.get(
            street="Calle Corredera",
            city="Madrid",
        )
        self.assertEqual(property_obj.block, "B")
        self.assertEqual(property_obj.floor, "2º")
        self.assertEqual(property_obj.door, "A")

    def test_address_suggestions_search_arcos_streets(self):
        Street.objects.create(
            name="Calle Corredera de otra ciudad",
            municipality="Jerez de la Frontera",
        )

        response = self.client.get(
            reverse("property_address_suggestions"),
            {"q": "Corre"},
        )

        self.assertEqual(response.status_code, 200)
        suggestions = response.json()["suggestions"]
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["street"], self.suggested_street.name)
        self.assertEqual(suggestions[0]["city"], "Arcos de la Frontera")

    def test_address_suggestions_require_two_characters(self):
        response = self.client.get(
            reverse("property_address_suggestions"),
            {"q": "C"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"suggestions": []})

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

    @patch("properties.views.geocode_address")
    def test_editing_fake_property_without_changing_address_does_not_geocode(
        self,
        geocode_mock,
    ):
        response = self.client.post(
            reverse("property_update", args=[self.property.pk]),
            {
                "street": self.property.street,
                "number": self.property.number,
                "city": self.property.city,
                "zone": self.second_zone.pk,
                "property_type": self.property.property_type,
                "occupied_by": "owner",
            },
        )

        self.assertRedirects(
            response,
            reverse("property_detail", args=[self.property.pk]),
        )
        geocode_mock.assert_not_called()
        self.property.refresh_from_db()
        self.assertIsNone(self.property.latitude)
        self.assertIsNone(self.property.longitude)

    @patch("properties.views.geocode_address")
    def test_new_arcos_property_is_geocoded_automatically(self, geocode_mock):
        geocode_mock.return_value = GeocodingResult(
            latitude=Decimal("36.750900"),
            longitude=Decimal("-5.806700"),
            source="CartoCiudad",
        )

        response = self.client.post(
            reverse("property_create"),
            {
                "street": "Calle Corredera",
                "number": "12",
                "city": "Arcos de la Frontera",
                "province": "Cádiz",
                "zone": self.first_zone.pk,
                "property_type": "house",
                "occupied_by": "owner",
            },
        )

        self.assertRedirects(response, reverse("properties"))
        property_obj = Property.objects.get(street="Calle Corredera")
        self.assertEqual(property_obj.latitude, Decimal("36.750900"))
        self.assertEqual(property_obj.longitude, Decimal("-5.806700"))
        geocode_mock.assert_called_once()

    @patch("properties.views.geocode_address")
    def test_changing_fake_address_to_arcos_geocodes_old_property(
        self,
        geocode_mock,
    ):
        geocode_mock.return_value = GeocodingResult(
            latitude=Decimal("36.751100"),
            longitude=Decimal("-5.807200"),
            source="CartoCiudad",
        )

        response = self.client.post(
            reverse("property_update", args=[self.property.pk]),
            {
                "street": "Calle Matrera",
                "number": "8",
                "city": "Arcos de la Frontera",
                "province": "Cádiz",
                "zone": self.first_zone.pk,
                "property_type": self.property.property_type,
                "occupied_by": "owner",
            },
        )

        self.assertRedirects(
            response,
            reverse("property_detail", args=[self.property.pk]),
        )
        self.property.refresh_from_db()
        self.assertEqual(self.property.latitude, Decimal("36.751100"))
        self.assertEqual(self.property.longitude, Decimal("-5.807200"))
        geocode_mock.assert_called_once()

    @patch("properties.views.geocode_address")
    def test_changed_address_replaces_previous_coordinates(self, geocode_mock):
        self.property.latitude = Decimal("40.416800")
        self.property.longitude = Decimal("-3.703800")
        self.property.save(update_fields=["latitude", "longitude"])
        geocode_mock.return_value = GeocodingResult(
            latitude=Decimal("36.752300"),
            longitude=Decimal("-5.810100"),
            source="CartoCiudad",
        )

        response = self.client.post(
            reverse("property_update", args=[self.property.pk]),
            {
                "street": "Calle Nueva Real",
                "number": "4",
                "city": "Arcos de la Frontera",
                "province": "Cádiz",
                "latitude": "",
                "longitude": "",
                "zone": self.first_zone.pk,
                "property_type": self.property.property_type,
                "occupied_by": "owner",
            },
        )

        self.assertRedirects(
            response,
            reverse("property_detail", args=[self.property.pk]),
        )
        self.property.refresh_from_db()
        self.assertEqual(self.property.latitude, Decimal("36.752300"))
        self.assertEqual(self.property.longitude, Decimal("-5.810100"))

    @patch("properties.views.geocode_address")
    def test_manual_map_coordinates_take_priority(self, geocode_mock):
        response = self.client.post(
            reverse("property_create"),
            {
                "street": "Calle Manual",
                "number": "3",
                "city": "Arcos de la Frontera",
                "province": "Cádiz",
                "latitude": "36.752000",
                "longitude": "-5.808000",
                "zone": self.first_zone.pk,
                "property_type": "flat",
                "occupied_by": "vacant",
            },
        )

        self.assertRedirects(response, reverse("properties"))
        geocode_mock.assert_not_called()
        property_obj = Property.objects.get(street="Calle Manual")
        self.assertEqual(property_obj.latitude, Decimal("36.752000"))
        self.assertEqual(property_obj.longitude, Decimal("-5.808000"))

    @patch("properties.views.geocode_address")
    def test_geocoding_endpoint_returns_preview_coordinates(self, geocode_mock):
        geocode_mock.return_value = GeocodingResult(
            latitude=Decimal("36.750900"),
            longitude=Decimal("-5.806700"),
            source="CartoCiudad",
            label="Calle Corredera 12",
        )

        response = self.client.post(
            reverse("property_geocode"),
            {
                "street": "Calle Corredera",
                "number": "12",
                "city": "Arcos de la Frontera",
                "province": "Cádiz",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["latitude"], "36.750900")
        self.assertEqual(response.json()["source"], "CartoCiudad")


class PropertyGeocodingTests(TestCase):
    @patch("properties.geocoding._geocode_with_nominatim")
    @patch("properties.geocoding._geocode_with_cartociudad")
    def test_geocoder_uses_fallback_and_caches_result(
        self,
        cartociudad_mock,
        nominatim_mock,
    ):
        cartociudad_mock.return_value = None
        nominatim_mock.return_value = GeocodingResult(
            latitude=Decimal("36.750900"),
            longitude=Decimal("-5.806700"),
            source="OpenStreetMap Nominatim",
        )

        first_result = geocode_address(
            "Calle Cache Única",
            "17",
            "11630",
            "Arcos de la Frontera",
            "Cádiz",
        )
        second_result = geocode_address(
            "Calle Cache Única",
            "17",
            "11630",
            "Arcos de la Frontera",
            "Cádiz",
        )

        self.assertEqual(first_result, second_result)
        cartociudad_mock.assert_called_once()
        nominatim_mock.assert_called_once()

    @patch("properties.geocoding._geocode_with_cartociudad")
    def test_geocoder_ignores_non_arcos_addresses(self, provider_mock):
        result = geocode_address(
            "Calle Inventada",
            "1",
            city="Madrid",
            province="Madrid",
        )

        self.assertIsNone(result)
        provider_mock.assert_not_called()


class PropertyMapViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="property-map-user",
            password="test-password",
            role="agent",
        )
        self.zone = Zone.objects.create(name="Centro mapa")
        self.located_property = Property.objects.create(
            street="Calle Localizada",
            number="10",
            city="Arcos de la Frontera",
            province="Cádiz",
            property_type="flat",
            zone=self.zone,
            latitude=Decimal("36.750900"),
            longitude=Decimal("-5.806700"),
        )
        self.pending_property = Property.objects.create(
            street="Calle Ficticia Pendiente",
            number="99",
            city="Madrid",
            property_type="house",
        )
        self.client.force_login(self.user)

    def test_property_list_links_to_global_map(self):
        response = self.client.get(reverse("properties"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("property_map"))
        self.assertContains(response, "Ver mapa")

    def test_map_only_includes_geolocated_properties(self):
        response = self.client.get(reverse("property_map"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["displayed_count"], 1)
        self.assertEqual(response.context["geolocated_total"], 1)
        self.assertEqual(response.context["pending_location_count"], 1)
        features = response.context["property_map_data"]["features"]
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0]["id"], str(self.located_property.pk))
        self.assertContains(response, self.located_property.full_address)
        self.assertNotContains(response, self.pending_property.full_address)
        self.assertContains(response, "/static/leaflet.css")
        self.assertContains(response, "/static/leaflet.js")
        self.assertNotContains(response, "unpkg.com/leaflet")
        self.assertContains(response, "property-map-pin")
        self.assertContains(response, "L.divIcon")
        self.assertContains(
            response,
            reverse("property_detail", args=[self.located_property.pk]),
        )

    def test_map_filters_geolocated_properties(self):
        response = self.client.get(
            reverse("property_map"),
            {"type": "house"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["displayed_count"], 0)
        self.assertEqual(response.context["property_map_data"]["features"], [])
        self.assertContains(response, "No hay inmuebles geolocalizados")


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
