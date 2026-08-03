from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from contacts.models import Contact
from listings.models import Listing
from news.models import News
from properties.models import Property

from .models import Appointment


class AppointmentResultFlowTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="appointment-agent",
            password="test-password",
        )
        self.property = Property.objects.create(
            street="Calle Mayor",
            number="10",
            city="Madrid",
            property_type="local",
        )
        self.contact = Contact.objects.create(
            name="Ana",
            phone="600000000",
            contact_type="owner",
        )
        self.contact.properties.add(self.property)
        self.news = News.objects.create(
            related_property=self.property,
            agent=self.user,
            motivation="sale",
            client_price="250000",
            estimated_price="240000",
        )
        self.appointment = Appointment.objects.create(
            related_property=self.property,
            contact=self.contact,
            agent=self.user,
            appointment_type="acquisition",
            date=date(2026, 8, 10),
            time=time(10, 0),
            news=self.news,
        )
        self.client.force_login(self.user)

    def test_appointment_asks_for_comment_before_showing_outcome(self):
        response = self.client.get(
            reverse("appointment_detail", args=[self.appointment.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Guardar comentario y completar cita")
        self.assertNotContains(response, "¿Cita con éxito?")

    def test_adding_comment_completes_appointment_and_shows_decision(self):
        response = self.client.post(
            reverse("appointment_add_result", args=[self.appointment.pk]),
            {"result_comment": "La visita fue positiva."},
            follow=True,
        )

        self.appointment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.appointment.status, "completed")
        self.assertEqual(
            self.appointment.result_comment,
            "La visita fue positiva.",
        )
        self.assertContains(response, "¿Cita con éxito?")
        self.assertContains(response, "Sí, crear encargo")
        self.assertContains(response, "No, programar llamada")

    def test_empty_comment_does_not_complete_appointment(self):
        response = self.client.post(
            reverse("appointment_add_result", args=[self.appointment.pk]),
            {"result_comment": "   "},
        )

        self.appointment.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.appointment.status, "scheduled")
        self.assertFalse(self.appointment.result_comment)

    def test_listing_cannot_be_created_before_comment(self):
        response = self.client.post(
            reverse("create_listing", args=[self.appointment.pk])
        )

        self.assertRedirects(
            response,
            reverse("appointment_detail", args=[self.appointment.pk]),
        )
        self.assertFalse(Listing.objects.exists())

    def test_successful_appointment_creates_listing(self):
        self.appointment.status = "completed"
        self.appointment.result_comment = "El propietario acepta el encargo."
        self.appointment.save()

        form_response = self.client.get(
            reverse("create_listing", args=[self.appointment.pk])
        )

        self.appointment.refresh_from_db()
        self.assertEqual(form_response.status_code, 200)
        self.assertContains(form_response, "Completa las condiciones acordadas")
        self.assertFalse(Listing.objects.exists())
        self.assertIsNone(self.appointment.result_success)

        response = self.client.post(
            reverse("create_listing", args=[self.appointment.pk]),
            {
                "owner": self.contact.pk,
                "start_date": "2026-08-11",
                "end_date": "2027-02-11",
                "commission_percent": "3.50",
                "is_exclusive": "on",
            },
        )

        listing = Listing.objects.get()
        self.appointment.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("listing_detail", args=[listing.pk]),
        )
        self.assertEqual(listing.source_appointment, self.appointment)
        self.assertEqual(listing.owner, self.contact)
        self.assertEqual(listing.agent, self.user)
        self.assertEqual(str(listing.commission_percent), "3.50")
        self.assertEqual(str(listing.start_date), "2026-08-11")
        self.assertEqual(str(listing.end_date), "2027-02-11")
        self.assertTrue(listing.is_exclusive)
        self.assertIs(self.appointment.result_success, True)

    def test_listing_form_rejects_end_date_before_start_date(self):
        self.appointment.status = "completed"
        self.appointment.result_comment = "El propietario acepta el encargo."
        self.appointment.save()

        response = self.client.post(
            reverse("create_listing", args=[self.appointment.pk]),
            {
                "owner": self.contact.pk,
                "start_date": "2026-08-11",
                "end_date": "2026-08-10",
                "commission_percent": "3.00",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "La fecha de conclusión no puede ser anterior al inicio.",
        )
        self.assertFalse(Listing.objects.exists())

    def test_listing_form_rejects_owner_from_another_property(self):
        other_owner = Contact.objects.create(
            name="Propietario ajeno",
            phone="611111111",
            contact_type="owner",
        )
        self.appointment.status = "completed"
        self.appointment.result_comment = "El propietario acepta el encargo."
        self.appointment.save()

        response = self.client.post(
            reverse("create_listing", args=[self.appointment.pk]),
            {
                "owner": other_owner.pk,
                "start_date": "2026-08-11",
                "end_date": "2027-02-11",
                "commission_percent": "3.00",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "owner",
            "Selecciona un propietario asociado a este inmueble.",
        )
        self.assertFalse(Listing.objects.exists())

    def test_unsuccessful_appointment_starts_call_flow(self):
        self.appointment.status = "completed"
        self.appointment.result_comment = "El propietario necesita más tiempo."
        self.appointment.save()

        response = self.client.post(
            reverse("appointment_schedule_call", args=[self.appointment.pk])
        )

        self.appointment.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("create_call", args=[self.news.pk]),
            fetch_redirect_response=False,
        )
        self.assertIs(self.appointment.result_success, False)
