from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from calendar_app.models import Appointment, Call
from contacts.models import Contact
from properties.models import Property

from .models import Listing, ListingComment


class ListingFollowUpTests(TestCase):
    def setUp(self):
        self.agent = get_user_model().objects.create_user(
            username="listing-agent",
            password="test-password",
        )
        self.property = Property.objects.create(
            street="Calle Encargo",
            number="20",
            city="Madrid",
            property_type="flat",
        )
        self.owner = Contact.objects.create(
            name="Propietaria",
            phone="600000003",
            contact_type="owner",
        )
        self.owner.properties.add(self.property)
        self.listing = Listing.objects.create(
            property=self.property,
            owner=self.owner,
            listing_type="sale",
            owner_price="250000",
            agency_price="240000",
            price_diference="10000",
            commission_amount="7200.00",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 2, 1),
            agent=self.agent,
        )
        self.client.force_login(self.agent)

    def test_add_comment_to_listing(self):
        response = self.client.post(
            reverse("listing_add_comment", args=[self.listing.pk]),
            {"text": "Se actualiza la estrategia comercial."},
        )

        comment = ListingComment.objects.get()
        self.assertRedirects(
            response,
            reverse("listing_detail", args=[self.listing.pk]),
        )
        self.assertEqual(comment.user, self.agent)
        self.assertEqual(comment.listing, self.listing)

    def test_schedule_follow_up_appointment(self):
        response = self.client.post(
            reverse("create_listing_appointment", args=[self.listing.pk]),
            {
                "date": "2026-08-20",
                "time": "10:00",
                "end_time": "11:00",
                "notes": "Revisar evolución del encargo.",
            },
        )

        appointment = Appointment.objects.get()
        self.assertRedirects(
            response,
            reverse("listing_detail", args=[self.listing.pk]),
        )
        self.assertEqual(appointment.appointment_type, "follow_up")
        self.assertEqual(appointment.listing, self.listing)
        self.assertEqual(appointment.contact, self.owner)
        self.assertEqual(appointment.agent, self.agent)
        self.listing.refresh_from_db()
        self.assertEqual(
            self.listing.workflow_status,
            "follow_up_appointment",
        )

    def test_follow_up_requires_comment_to_complete(self):
        appointment = Appointment.objects.create(
            related_property=self.property,
            contact=self.owner,
            agent=self.agent,
            appointment_type="follow_up",
            date="2026-08-20",
            time="10:00",
            end_time="11:00",
            listing=self.listing,
        )

        response = self.client.get(
            reverse(
                "appointment_update_status",
                args=[appointment.pk, "completed"],
            )
        )
        appointment.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("appointment_detail", args=[appointment.pk]),
        )
        self.assertEqual(appointment.status, "scheduled")

        response = self.client.post(
            reverse("appointment_add_result", args=[appointment.pk]),
            {"result_comment": "El propietario mantiene el encargo activo."},
            follow=True,
        )
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "completed")
        self.assertEqual(
            appointment.result_comment,
            "El propietario mantiene el encargo activo.",
        )
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.workflow_status, "active")
        self.assertContains(response, "Seguimiento completado")

    def test_schedule_call_from_listing(self):
        response = self.client.post(
            reverse("create_listing_call", args=[self.listing.pk]),
            {
                "date": "2026-08-21",
                "time": "11:00",
                "notes": "Confirmar disponibilidad.",
            },
        )

        call = Call.objects.get()
        self.assertRedirects(
            response,
            reverse("listing_detail", args=[self.listing.pk]),
        )
        self.assertEqual(call.listing, self.listing)
        self.assertEqual(call.contact, self.owner)
        self.assertEqual(call.agent, self.agent)

    def test_listing_detail_contains_follow_up_history(self):
        ListingComment.objects.create(
            listing=self.listing,
            user=self.agent,
            text="Comentario de prueba.",
        )
        response = self.client.get(
            reverse("listing_detail", args=[self.listing.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comentario de prueba.")
        self.assertContains(response, "Cita de seguimiento")
