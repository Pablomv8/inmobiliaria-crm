from datetime import date, datetime, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from contacts.models import Contact
from listings.models import Listing
from news.models import News
from orders.models import Order
from properties.models import Property, Zone
from tasks.models import Task

from .forms import AppointmentForm, CallForm
from .models import (
    Appointment,
    Call,
    CallComment,
    CounterOffer,
    ProposalAppointment,
)


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
            end_time=time(11, 0),
            news=self.news,
        )
        self.client.force_login(self.user)

    def test_acquisition_form_has_its_type_fixed_automatically(self):
        response = self.client.get(
            reverse("create_appointment", args=[self.news.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("appointment_type", response.context["form"].fields)
        self.assertContains(response, "Nueva cita de adquisición")
        self.assertNotContains(response, "Tipo de cita")

    def test_acquisition_form_creates_the_fixed_type_without_posting_it(self):
        response = self.client.post(
            reverse("create_appointment", args=[self.news.pk]),
            {
                "date": "2026-08-11",
                "time": "11:00",
                "end_time": "12:00",
                "notes": "Primera reunión con la propiedad.",
            },
        )

        self.assertRedirects(
            response,
            reverse("news_detail", args=[self.news.pk]),
        )
        created_appointment = Appointment.objects.exclude(
            pk=self.appointment.pk
        ).get()
        self.assertEqual(created_appointment.appointment_type, "acquisition")
        self.assertEqual(created_appointment.news, self.news)

    def test_appointment_asks_for_comment_before_showing_outcome(self):
        self.news.refresh_from_db()
        response = self.client.get(
            reverse("appointment_detail", args=[self.appointment.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.news.status, "appointment")
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
        self.property.refresh_from_db()
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
        self.assertEqual(self.property.status, "active")
        self.news.refresh_from_db()
        self.assertEqual(self.news.status, "closed")


class AppointmentEditTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.agent = user_model.objects.create_user(
            username="edit-appointment-agent",
            password="test-password",
            role="agent",
        )
        self.new_agent = user_model.objects.create_user(
            username="edit-appointment-new-agent",
            password="test-password",
            role="agent",
        )
        self.property = Property.objects.create(
            street="Calle Edición",
            number="4",
            city="Madrid",
            property_type="office",
        )
        self.contact = Contact.objects.create(
            name="Contacto edición",
            phone="600444555",
            contact_type="buyer",
            assigned_agent=self.agent,
        )
        self.appointment = Appointment.objects.create(
            related_property=self.property,
            contact=self.contact,
            agent=self.agent,
            appointment_type="valuation",
            date=date(2026, 10, 5),
            time=time(10, 0),
            end_time=time(11, 0),
            notes="Notas iniciales.",
        )
        self.client.force_login(self.agent)

    def test_detail_and_edit_form_allow_editing_the_appointment(self):
        detail_response = self.client.get(
            reverse("appointment_detail", args=[self.appointment.pk])
        )
        form_response = self.client.get(
            reverse("appointment_update", args=[self.appointment.pk])
        )

        self.assertContains(detail_response, "Editar cita")
        self.assertEqual(form_response.status_code, 200)
        self.assertContains(form_response, "Agente asignado")
        self.assertContains(form_response, 'name="agent"', html=False)
        self.assertContains(form_response, self.new_agent.username)
        self.assertNotContains(form_response, 'name="appointment_type"', html=False)

    def test_owner_can_reassign_and_reschedule_the_appointment(self):
        response = self.client.post(
            reverse("appointment_update", args=[self.appointment.pk]),
            {
                "agent": self.new_agent.pk,
                "date": "2026-10-06",
                "time": "11:30",
                "end_time": "12:30",
                "notes": "La atenderá el nuevo responsable.",
            },
        )

        self.appointment.refresh_from_db()
        self.assertRedirects(
            response,
            f"{reverse('calendar')}?agents={self.new_agent.pk}",
        )
        self.assertEqual(self.appointment.agent, self.new_agent)
        self.assertEqual(self.appointment.date, date(2026, 10, 6))
        self.assertEqual(self.appointment.time, time(11, 30))
        self.assertEqual(self.appointment.end_time, time(12, 30))
        self.assertEqual(
            self.appointment.notes,
            "La atenderá el nuevo responsable.",
        )

    def test_reassignment_rejects_the_new_agents_occupied_time(self):
        Appointment.objects.create(
            related_property=self.property,
            contact=self.contact,
            agent=self.new_agent,
            appointment_type="sale",
            date=date(2026, 10, 6),
            time=time(11, 30),
            end_time=time(12, 30),
        )

        response = self.client.post(
            reverse("appointment_update", args=[self.appointment.pk]),
            {
                "agent": self.new_agent.pk,
                "date": "2026-10-06",
                "time": "11:30",
                "end_time": "12:30",
                "notes": "Horario ocupado.",
            },
        )

        self.appointment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "El agente seleccionado ya tiene otra cita, llamada o tarea en ese intervalo.",
        )
        self.assertEqual(self.appointment.agent, self.agent)
        self.assertEqual(self.appointment.date, date(2026, 10, 5))

    def test_an_agent_cannot_edit_another_agents_appointment(self):
        self.client.force_login(self.new_agent)

        response = self.client.get(
            reverse("appointment_update", args=[self.appointment.pk])
        )

        self.assertEqual(response.status_code, 404)


class TaskCalendarIntegrationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.agent = user_model.objects.create_user(
            username="calendar-task-agent",
            password="test-password",
            role="agent",
        )
        self.other_agent = user_model.objects.create_user(
            username="calendar-task-other",
            password="test-password",
            role="agent",
        )
        self.manager = user_model.objects.create_user(
            username="calendar-task-manager",
            password="test-password",
            role="manager",
        )
        self.zone = Zone.objects.create(name="Zona agenda")
        self.custom_task = Task.objects.create(
            task_type="custom",
            title="Preparar informe",
            description="Preparar el informe semanal.",
            assigned_to=self.agent,
            due_date=timezone.make_aware(datetime(2026, 9, 7, 10, 0)),
        )
        self.zone_task = Task.objects.create(
            task_type="zone_sweep",
            zone=self.zone,
            assigned_to=self.agent,
            schedule_date=date(2026, 9, 8),
            start_time=time(14, 0),
            end_time=time(16, 0),
            repeat_days=3,
        )
        self.completed_task = Task.objects.create(
            task_type="custom",
            title="Tarea completada",
            description="No debe mostrarse.",
            assigned_to=self.agent,
            due_date=timezone.make_aware(datetime(2026, 9, 7, 12, 0)),
            status="done",
        )
        self.other_task = Task.objects.create(
            task_type="custom",
            title="Tarea de otro agente",
            description="No pertenece al agente principal.",
            assigned_to=self.other_agent,
            due_date=timezone.make_aware(datetime(2026, 9, 7, 13, 0)),
        )
        self.client.force_login(self.agent)

    def test_task_occurrences_are_returned_by_calendar_events(self):
        events = self.client.get(reverse("calendar_events")).json()
        event_ids = {event["id"] for event in events}

        self.assertIn(f"task-{self.custom_task.pk}-0", event_ids)
        self.assertIn(f"task-{self.zone_task.pk}-0", event_ids)
        self.assertIn(f"task-{self.zone_task.pk}-1", event_ids)
        self.assertIn(f"task-{self.zone_task.pk}-2", event_ids)
        self.assertNotIn(f"task-{self.completed_task.pk}-0", event_ids)
        self.assertIn(f"task-{self.other_task.pk}-0", event_ids)

        custom_event = next(
            event
            for event in events
            if event["id"] == f"task-{self.custom_task.pk}-0"
        )
        self.assertIn("2026-09-07T10:00:00", custom_event["start"])
        self.assertIn("2026-09-07T11:00:00", custom_event["end"])
        self.assertEqual(
            custom_event["url"],
            reverse("task_detail", args=[self.custom_task.pk]),
        )

    def test_tasks_are_in_mobile_calendar_and_agenda_views(self):
        calendar_response = self.client.get(reverse("calendar"))
        calendar_task_events = [
            event
            for _, events in calendar_response.context["agenda_by_day"]
            for event in events
            if event["type"] == "task"
        ]
        agenda_response = self.client.get(reverse("agenda"))
        agenda_task_events = [
            event
            for event in agenda_response.context["events"]
            if event["type"] == "task"
        ]

        self.assertEqual(len(calendar_task_events), 5)
        self.assertEqual(len(agenda_task_events), 5)
        self.assertContains(calendar_response, "Peinar zona Zona agenda")
        self.assertContains(agenda_response, "Preparar informe")
        self.assertContains(calendar_response, self.other_agent.username)

    def test_any_user_can_filter_the_calendar_by_another_agent(self):
        events = self.client.get(
            reverse("calendar_events"),
            {"agents": self.other_agent.pk},
        ).json()
        event_ids = {event["id"] for event in events}

        self.assertIn(f"task-{self.other_task.pk}-0", event_ids)
        self.assertNotIn(f"task-{self.custom_task.pk}-0", event_ids)
        self.assertNotIn(f"task-{self.zone_task.pk}-0", event_ids)

        calendar_response = self.client.get(reverse("calendar"))
        self.assertContains(calendar_response, "Filtrar agendas")
        self.assertContains(calendar_response, self.other_agent.username)

    def test_tasks_block_all_overlapping_available_slots(self):
        custom_response = self.client.get(
            reverse("available_slots"),
            {"date": "2026-09-07"},
        )
        zone_response = self.client.get(
            reverse("available_slots"),
            {"date": "2026-09-09"},
        )

        self.assertIn("10:00", custom_response.json()["occupied"])
        self.assertIn("10:30", custom_response.json()["occupied"])
        self.assertIn("14:00", zone_response.json()["occupied"])
        self.assertIn("14:30", zone_response.json()["occupied"])
        self.assertIn("15:00", zone_response.json()["occupied"])
        self.assertIn("15:30", zone_response.json()["occupied"])
        self.assertNotIn("16:00", zone_response.json()["occupied"])

    def test_appointment_and_call_forms_reject_a_task_time(self):
        appointment_form = AppointmentForm(
            data={
                "appointment_type": "valuation",
                "date": "2026-09-07",
                "time": "10:30",
                "end_time": "11:30",
                "notes": "",
            },
            user=self.agent,
        )
        call_form = CallForm(
            data={
                "date": "2026-09-07",
                "time": "10:30",
                "notes": "",
            },
            user=self.agent,
        )

        self.assertFalse(appointment_form.is_valid())
        self.assertFalse(call_form.is_valid())
        self.assertIn("cita, llamada o tarea", appointment_form.non_field_errors()[0])
        self.assertIn("cita, llamada o tarea", call_form.non_field_errors()[0])


class SaleAppointmentFlowTests(TestCase):
    def setUp(self):
        self.agent = get_user_model().objects.create_user(
            username="sales-agent",
            password="test-password",
        )
        self.buyer = Contact.objects.create(
            name="Comprador",
            phone="600100100",
            contact_type="buyer",
            assigned_agent=self.agent,
        )
        self.owner = Contact.objects.create(
            name="Propietaria venta",
            phone="600200200",
            contact_type="owner",
        )
        self.zone = Zone.objects.create(name="Centro ventas")
        self.property = Property.objects.create(
            street="Calle Venta",
            number="5",
            city="Madrid",
            property_type="flat",
            zone=self.zone,
            bedrooms=3,
            bathrooms=2,
        )
        self.listing = Listing.objects.create(
            property=self.property,
            owner=self.owner,
            listing_type="sale",
            owner_price="245000",
            agency_price="250000",
            price_diference="5000",
            commission_percent="3.00",
            agent=self.agent,
        )
        self.order = Order.objects.create(
            buyer=self.buyer,
            zone=self.zone,
            max_price="275000",
            payment_type="financing",
            property_type="flat",
            bedrooms=2,
            bathrooms=1,
        )
        self.client.force_login(self.agent)

    def create_sale_appointment(self):
        response = self.client.post(
            reverse("create_order_sale_appointment", args=[self.order.pk]),
            {
                "listing": self.listing.pk,
                "date": "2026-08-22",
                "time": "12:00",
                "end_time": "13:00",
                "notes": "Visita comercial.",
            },
        )
        return response, Appointment.objects.get()

    def create_registered_proposal(self):
        proposal_meeting = Appointment.objects.create(
            related_property=self.property,
            contact=self.buyer,
            agent=self.agent,
            appointment_type="proposal",
            date=date(2026, 8, 24),
            time=time(13, 0),
            end_time=time(14, 0),
            listing=self.listing,
            order=self.order,
            status="completed",
            result_comment="Se presenta la oferta.",
        )
        return ProposalAppointment.objects.create(
            source_sale_appointment=proposal_meeting,
            order=self.order,
            listing=self.listing,
            buyer=self.buyer,
            agent=self.agent,
            listing_price="250000",
            offered_price="242000",
            deposit_amount="5000",
            proposal_date=date(2026, 8, 24),
            end_date=date(2026, 8, 29),
        )

    def test_order_creates_sale_appointment_linked_to_listing(self):
        response, appointment = self.create_sale_appointment()

        self.assertRedirects(response, reverse("order_detail", args=[self.order.pk]))
        self.assertEqual(appointment.appointment_type, "sale")
        self.assertEqual(appointment.order, self.order)
        self.assertEqual(appointment.listing, self.listing)
        self.assertEqual(appointment.related_property, self.property)
        self.assertEqual(appointment.contact, self.buyer)
        self.assertEqual(appointment.agent, self.agent)
        self.order.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertEqual(self.order.status, "sale_appointment")
        self.assertEqual(self.listing.workflow_status, "sale_appointment")

    def test_sale_comment_completes_visit_and_asks_about_proposal(self):
        _, appointment = self.create_sale_appointment()
        response = self.client.post(
            reverse("appointment_add_result", args=[appointment.pk]),
            {"result_comment": "El inmueble le interesa."},
            follow=True,
        )

        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "completed")
        self.assertContains(
            response,
            "¿El comprador quiere hacer una propuesta de compra?",
        )

    def test_positive_sale_result_schedules_proposal_appointment(self):
        _, appointment = self.create_sale_appointment()
        appointment.status = "completed"
        appointment.result_comment = "Quiere presentar una oferta."
        appointment.save()

        response = self.client.post(
            reverse("create_proposal_appointment", args=[appointment.pk]),
            {
                "date": "2026-08-24",
                "time": "13:00",
                "end_time": "14:00",
                "notes": "Reunión para concretar la oferta.",
            },
        )

        proposal_appointment = Appointment.objects.get(appointment_type="proposal")
        appointment.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("appointment_detail", args=[proposal_appointment.pk]),
        )
        self.assertEqual(proposal_appointment.source_sale_appointment, appointment)
        self.assertEqual(proposal_appointment.order, self.order)
        self.assertEqual(proposal_appointment.listing, self.listing)
        self.assertEqual(proposal_appointment.contact, self.buyer)
        self.assertEqual(proposal_appointment.status, "scheduled")
        self.assertIs(appointment.result_success, True)
        self.order.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertEqual(self.order.status, "proposal_appointment")
        self.assertEqual(self.listing.workflow_status, "proposal_appointment")

        calendar_response = self.client.get(reverse("calendar_events"))
        self.assertContains(calendar_response, "Cita de Propuesta")

    def test_completed_proposal_appointment_creates_purchase_proposal(self):
        _, sale_appointment = self.create_sale_appointment()
        sale_appointment.status = "completed"
        sale_appointment.result_comment = "Quiere presentar una oferta."
        sale_appointment.result_success = True
        sale_appointment.save()
        proposal_appointment = Appointment.objects.create(
            related_property=self.property,
            contact=self.buyer,
            agent=self.agent,
            appointment_type="proposal",
            date=date(2026, 8, 24),
            time=time(13, 0),
            end_time=time(14, 0),
            listing=self.listing,
            order=self.order,
            source_sale_appointment=sale_appointment,
        )

        comment_response = self.client.post(
            reverse("appointment_add_result", args=[proposal_appointment.pk]),
            {"result_comment": "Se acuerdan las condiciones de la oferta."},
            follow=True,
        )
        proposal_appointment.refresh_from_db()
        self.assertEqual(proposal_appointment.status, "completed")
        self.assertContains(comment_response, "Crear propuesta de compra")

        response = self.client.post(
            reverse("create_purchase_proposal", args=[proposal_appointment.pk]),
            {
                "offered_price": "242000",
                "deposit_amount": "5000",
                "proposal_date": "2026-08-24",
                "end_date": "2026-08-29",
            },
        )

        proposal = ProposalAppointment.objects.get()
        self.assertRedirects(
            response,
            reverse("proposal_appointment_detail", args=[proposal.pk]),
        )
        self.assertEqual(
            proposal.source_sale_appointment,
            proposal_appointment,
        )
        self.assertEqual(proposal.order, self.order)
        self.assertEqual(proposal.listing, self.listing)
        self.assertEqual(str(proposal.listing_price), "250000.00")
        self.assertEqual(str(proposal.offered_price), "242000.00")
        self.order.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertEqual(self.order.status, "proposal")
        self.assertEqual(self.listing.workflow_status, "proposal")

        listing_response = self.client.get(
            reverse("listing_detail", args=[self.listing.pk])
        )
        self.assertContains(listing_response, "Propuestas de compra")
        self.assertContains(listing_response, "242000.00")

    def test_declining_proposal_records_decision(self):
        _, appointment = self.create_sale_appointment()
        appointment.status = "completed"
        appointment.result_comment = "No encaja con sus necesidades."
        appointment.save()

        response = self.client.post(
            reverse("decline_sale_proposal", args=[appointment.pk])
        )

        appointment.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("appointment_detail", args=[appointment.pk]),
        )
        self.assertIs(appointment.result_success, False)

    def test_registered_proposal_schedules_acceptance_appointment(self):
        proposal = self.create_registered_proposal()

        response = self.client.post(
            reverse("create_acceptance_appointment", args=[proposal.pk]),
            {
                "date": "2026-08-26",
                "time": "11:00",
                "end_time": "12:00",
                "notes": "Reunión con la propietaria.",
            },
        )

        acceptance = Appointment.objects.get(
            appointment_type="proposal_acceptance"
        )
        self.assertRedirects(
            response,
            reverse("appointment_detail", args=[acceptance.pk]),
        )
        self.assertEqual(acceptance.purchase_proposal, proposal)
        self.assertEqual(acceptance.order, self.order)
        self.assertEqual(acceptance.listing, self.listing)
        self.assertEqual(acceptance.contact, self.owner)
        proposal.refresh_from_db()
        self.order.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertEqual(proposal.status, "acceptance_appointment")
        self.assertEqual(self.order.status, "acceptance_appointment")
        self.assertEqual(self.listing.workflow_status, "acceptance_appointment")

    def test_accepted_proposal_can_schedule_contract_and_signing(self):
        proposal = self.create_registered_proposal()
        self.client.post(
            reverse("create_acceptance_appointment", args=[proposal.pk]),
            {"date": "2026-08-26", "time": "11:00", "end_time": "12:00", "notes": "Aceptación."},
        )
        acceptance = Appointment.objects.get(
            appointment_type="proposal_acceptance"
        )
        self.client.post(
            reverse("appointment_add_result", args=[acceptance.pk]),
            {"result_comment": "La propietaria acepta la oferta."},
        )

        contract_response = self.client.post(
            reverse(
                "create_post_acceptance_appointment",
                args=[acceptance.pk, "contract"],
            ),
            {"date": "2026-08-27", "time": "12:00", "end_time": "13:00", "notes": "Contrato."},
        )
        signing_response = self.client.post(
            reverse(
                "create_post_acceptance_appointment",
                args=[acceptance.pk, "signing"],
            ),
            {"date": "2026-08-28", "time": "13:00", "end_time": "14:00", "notes": "Notaría."},
        )

        contract = Appointment.objects.get(appointment_type="contract")
        signing = Appointment.objects.get(appointment_type="signing")
        self.assertRedirects(
            contract_response,
            reverse("appointment_detail", args=[contract.pk]),
        )
        self.assertRedirects(
            signing_response,
            reverse("appointment_detail", args=[signing.pk]),
        )
        self.assertEqual(contract.source_acceptance_appointment, acceptance)
        self.assertEqual(signing.source_acceptance_appointment, acceptance)
        acceptance.refresh_from_db()
        proposal.refresh_from_db()
        self.order.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertIs(acceptance.result_success, True)
        self.assertEqual(proposal.status, "signing_appointment")
        self.assertEqual(self.order.status, "signing_appointment")
        self.assertEqual(self.listing.workflow_status, "signing_appointment")

        calendar_response = self.client.get(reverse("calendar_events"))
        calendar_titles = [event["title"] for event in calendar_response.json()]
        self.assertTrue(any("Cita de Contrato" in title for title in calendar_titles))
        self.assertTrue(
            any("Cita de Escrituración" in title for title in calendar_titles)
        )

    def test_rejected_proposal_creates_counteroffer_visible_from_contexts(self):
        proposal = self.create_registered_proposal()
        self.client.post(
            reverse("create_acceptance_appointment", args=[proposal.pk]),
            {"date": "2026-08-26", "time": "11:00", "end_time": "12:00", "notes": "Aceptación."},
        )
        acceptance = Appointment.objects.get(
            appointment_type="proposal_acceptance"
        )
        self.client.post(
            reverse("appointment_add_result", args=[acceptance.pk]),
            {"result_comment": "La propietaria solicita revisar el precio."},
        )

        response = self.client.post(
            reverse("create_counteroffer", args=[acceptance.pk]),
            {
                "counteroffer_date": "2026-08-26",
                "owner_price": "247000",
                "notes": "Mantiene el mobiliario incluido.",
            },
        )

        counteroffer = CounterOffer.objects.get()
        self.assertRedirects(
            response,
            reverse("counteroffer_detail", args=[counteroffer.pk]),
        )
        self.assertEqual(counteroffer.proposal, proposal)
        self.assertEqual(counteroffer.source_acceptance_appointment, acceptance)
        self.assertEqual(str(counteroffer.owner_price), "247000.00")
        acceptance.refresh_from_db()
        proposal.refresh_from_db()
        self.order.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertIs(acceptance.result_success, False)
        self.assertEqual(proposal.status, "counteroffer")
        self.assertEqual(self.order.status, "counteroffer")
        self.assertEqual(self.listing.workflow_status, "counteroffer")

        proposal_response = self.client.get(
            reverse("proposal_appointment_detail", args=[proposal.pk])
        )
        listing_response = self.client.get(
            reverse("listing_detail", args=[self.listing.pk])
        )
        self.assertContains(proposal_response, "247000.00")
        self.assertContains(listing_response, "247000.00")
        self.assertContains(
            proposal_response,
            reverse("counteroffer_detail", args=[counteroffer.pk]),
        )
        self.assertContains(
            listing_response,
            reverse("counteroffer_detail", args=[counteroffer.pk]),
        )

        counteroffer_response = self.client.get(
            reverse("counteroffer_detail", args=[counteroffer.pk])
        )
        self.assertContains(counteroffer_response, "Preparar nueva oferta")
        self.assertContains(
            counteroffer_response,
            reverse(
                "create_counteroffer_response_appointment",
                args=[counteroffer.pk],
            ),
        )

        response = self.client.post(
            reverse(
                "create_counteroffer_response_appointment",
                args=[counteroffer.pk],
            ),
            {
                "date": "2026-08-27",
                "time": "14:00",
                "end_time": "15:00",
                "notes": "Revisión de la oferta tras la contraoferta.",
            },
        )
        response_appointment = Appointment.objects.get(
            source_counteroffer=counteroffer,
        )
        self.assertRedirects(
            response,
            reverse("appointment_detail", args=[response_appointment.pk]),
        )
        self.assertEqual(response_appointment.appointment_type, "proposal")
        self.assertEqual(response_appointment.order, self.order)
        self.assertEqual(response_appointment.listing, self.listing)
        self.assertEqual(response_appointment.contact, self.buyer)
        self.order.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertEqual(self.order.status, "proposal_appointment")
        self.assertEqual(self.listing.workflow_status, "proposal_appointment")

        self.client.post(
            reverse("appointment_add_result", args=[response_appointment.pk]),
            {"result_comment": "El comprador mejora su oferta."},
        )
        response = self.client.post(
            reverse("create_purchase_proposal", args=[response_appointment.pk]),
            {
                "offered_price": "245000",
                "deposit_amount": "6000",
                "proposal_date": "2026-08-27",
                "end_date": "2026-09-01",
            },
        )
        new_proposal = ProposalAppointment.objects.exclude(pk=proposal.pk).get()
        self.assertRedirects(
            response,
            reverse("proposal_appointment_detail", args=[new_proposal.pk]),
        )
        self.assertEqual(
            new_proposal.source_sale_appointment,
            response_appointment,
        )
        self.assertEqual(
            new_proposal.source_sale_appointment.source_counteroffer,
            counteroffer,
        )
        self.assertEqual(str(new_proposal.offered_price), "245000.00")
        self.order.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertEqual(self.order.status, "proposal")
        self.assertEqual(self.listing.workflow_status, "proposal")

        counteroffer_response = self.client.get(
            reverse("counteroffer_detail", args=[counteroffer.pk])
        )
        listing_response = self.client.get(
            reverse("listing_detail", args=[self.listing.pk])
        )
        self.assertContains(counteroffer_response, "Ver nueva oferta")
        self.assertContains(
            counteroffer_response,
            reverse("proposal_appointment_detail", args=[new_proposal.pk]),
        )
        self.assertContains(listing_response, "Respuesta a la contraoferta")


class CallFlowTests(TestCase):
    def setUp(self):
        self.agent = get_user_model().objects.create_user(
            username="call-agent",
            password="test-password",
            role="agent",
        )
        self.property = Property.objects.create(
            street="Calle Llamada",
            number="7",
            city="Madrid",
            property_type="flat",
        )
        self.contact = Contact.objects.create(
            name="Contacto llamada",
            phone="600777777",
            contact_type="buyer",
            assigned_agent=self.agent,
        )
        self.call = Call.objects.create(
            contact=self.contact,
            agent=self.agent,
            date=date(2026, 9, 1),
            time=time(10, 0),
            status="pending",
        )
        self.client.force_login(self.agent)

    def test_call_accepts_comments_and_shows_them_in_detail(self):
        response = self.client.post(
            reverse("call_add_comment", args=[self.call.pk]),
            {"text": "El cliente solicita que volvamos a llamar por la tarde."},
        )

        comment = CallComment.objects.get()
        self.assertRedirects(
            response,
            reverse("call_detail", args=[self.call.pk]),
        )
        self.assertEqual(comment.call, self.call)
        self.assertEqual(comment.user, self.agent)

        detail_response = self.client.get(
            reverse("call_detail", args=[self.call.pk])
        )
        self.assertContains(detail_response, comment.text)

    def test_call_can_be_completed_cancelled_and_reactivated(self):
        for status in ["completed", "cancelled", "pending"]:
            with self.subTest(status=status):
                response = self.client.post(
                    reverse("call_update_status", args=[self.call.pk, status])
                )
                self.call.refresh_from_db()
                self.assertRedirects(
                    response,
                    reverse("call_detail", args=[self.call.pk]),
                )
                self.assertEqual(self.call.status, status)

    def test_cancelled_events_are_hidden_but_active_and_completed_remain(self):
        completed_call = Call.objects.create(
            contact=self.contact,
            agent=self.agent,
            date=date(2026, 9, 1),
            time=time(11, 0),
            status="completed",
        )
        cancelled_call = Call.objects.create(
            contact=self.contact,
            agent=self.agent,
            date=date(2026, 9, 1),
            time=time(12, 0),
            status="cancelled",
        )
        active_appointment = Appointment.objects.create(
            related_property=self.property,
            contact=self.contact,
            agent=self.agent,
            appointment_type="valuation",
            date=date(2026, 9, 2),
            time=time(10, 0),
            end_time=time(11, 0),
            status="scheduled",
        )
        cancelled_appointment = Appointment.objects.create(
            related_property=self.property,
            contact=self.contact,
            agent=self.agent,
            appointment_type="valuation",
            date=date(2026, 9, 2),
            time=time(11, 0),
            end_time=time(12, 0),
            status="cancelled",
        )

        calendar_response = self.client.get(reverse("calendar"))
        calendar_objects = {
            (event["type"], event["object"].pk)
            for _, events in calendar_response.context["agenda_by_day"]
            for event in events
        }
        self.assertIn(("call", self.call.pk), calendar_objects)
        self.assertIn(("call", completed_call.pk), calendar_objects)
        self.assertIn(("appointment", active_appointment.pk), calendar_objects)
        self.assertNotIn(("call", cancelled_call.pk), calendar_objects)
        self.assertNotIn(
            ("appointment", cancelled_appointment.pk),
            calendar_objects,
        )

        event_ids = {
            event["id"]
            for event in self.client.get(reverse("calendar_events")).json()
        }
        self.assertIn(f"call-{self.call.pk}", event_ids)
        self.assertIn(f"call-{completed_call.pk}", event_ids)
        self.assertNotIn(f"call-{cancelled_call.pk}", event_ids)
        self.assertNotIn(
            f"appointment-{cancelled_appointment.pk}",
            event_ids,
        )

        agenda_response = self.client.get(reverse("agenda"))
        agenda_objects = {
            (event["type"], event["object"].pk)
            for event in agenda_response.context["events"]
        }
        self.assertIn(("call", completed_call.pk), agenda_objects)
        self.assertNotIn(("call", cancelled_call.pk), agenda_objects)
        self.assertNotIn(
            ("appointment", cancelled_appointment.pk),
            agenda_objects,
        )


class AvailableSlotsTests(TestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user(
            username="slots-manager",
            password="test-password",
            role="manager",
        )
        self.agent = get_user_model().objects.create_user(
            username="slots-agent",
            password="test-password",
        )
        property_obj = Property.objects.create(
            street="Calle Horario",
            number="1",
            city="Madrid",
            property_type="local",
        )
        contact = Contact.objects.create(
            name="Contacto horario",
            phone="600300300",
            contact_type="owner",
        )
        Appointment.objects.create(
            related_property=property_obj,
            contact=contact,
            agent=self.agent,
            appointment_type="acquisition",
            date=date(2026, 8, 25),
            time=time(10, 30),
            end_time=time(12, 0),
        )

    def test_manager_sees_assigned_agents_acquisition_as_occupied(self):
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("available_slots"),
            {"date": "2026-08-25", "agent_id": self.agent.pk},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["occupied"], ["10:30", "11:00", "11:30"])
        self.assertEqual(
            payload["intervals"],
            [{
                "start": "10:30",
                "end": "12:00",
                "type": "appointment",
                "label": "Cita de Adquisición",
            }],
        )

    def test_appointment_form_rejects_overlap_and_accepts_exact_boundary(self):
        overlapping_form = AppointmentForm(
            data={
                "appointment_type": "valuation",
                "date": "2026-08-25",
                "time": "11:30",
                "end_time": "12:30",
                "notes": "Se solapa.",
            },
            user=self.agent,
        )
        boundary_form = AppointmentForm(
            data={
                "appointment_type": "valuation",
                "date": "2026-08-25",
                "time": "12:00",
                "end_time": "13:00",
                "notes": "Empieza al terminar la anterior.",
            },
            user=self.agent,
        )

        self.assertFalse(overlapping_form.is_valid())
        self.assertIn("se solapa", overlapping_form.non_field_errors()[0])
        self.assertTrue(boundary_form.is_valid(), boundary_form.errors)

    def test_appointment_form_rejects_end_before_start(self):
        form = AppointmentForm(
            data={
                "appointment_type": "valuation",
                "date": "2026-08-26",
                "time": "12:00",
                "end_time": "11:00",
                "notes": "Intervalo incorrecto.",
            },
            user=self.agent,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "posterior a la hora de inicio",
            form.errors["end_time"][0],
        )

    def test_completed_and_cancelled_events_leave_the_interval_free(self):
        existing = Appointment.objects.first()
        Appointment.objects.create(
            related_property=existing.related_property,
            contact=existing.contact,
            agent=self.agent,
            appointment_type="valuation",
            date=date(2026, 8, 26),
            time=time(9, 0),
            end_time=time(10, 0),
            status="completed",
        )
        Appointment.objects.create(
            related_property=existing.related_property,
            contact=existing.contact,
            agent=self.agent,
            appointment_type="valuation",
            date=date(2026, 8, 26),
            time=time(10, 0),
            end_time=time(11, 0),
            status="cancelled",
        )
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("available_slots"),
            {"date": "2026-08-26", "agent_id": self.agent.pk},
        )
        free_form = AppointmentForm(
            data={
                "appointment_type": "valuation",
                "date": "2026-08-26",
                "time": "09:30",
                "end_time": "10:30",
                "notes": "Coincide con eventos ya inactivos.",
            },
            user=self.agent,
        )

        self.assertEqual(response.json()["occupied"], [])
        self.assertEqual(response.json()["intervals"], [])
        self.assertTrue(free_form.is_valid(), free_form.errors)

    def test_agent_can_inspect_another_agents_calendar_and_slots(self):
        another_agent = get_user_model().objects.create_user(
            username="slots-other-agent",
            password="test-password",
        )
        self.client.force_login(another_agent)
        response = self.client.get(
            reverse("available_slots"),
            {"date": "2026-08-25", "agent_id": self.agent.pk},
        )

        self.assertIn("10:30", response.json()["occupied"])

        calendar_event_ids = {
            event["id"]
            for event in self.client.get(reverse("calendar_events")).json()
        }
        appointment = Appointment.objects.get(agent=self.agent)
        self.assertIn(f"appointment-{appointment.pk}", calendar_event_ids)
        calendar_event = next(
            event
            for event in self.client.get(reverse("calendar_events")).json()
            if event["id"] == f"appointment-{appointment.pk}"
        )
        self.assertEqual(calendar_event["end"], "2026-08-25T12:00:00")

        agenda_objects = {
            (event["type"], event["object"].pk)
            for event in self.client.get(reverse("agenda")).context["events"]
        }
        self.assertIn(("appointment", appointment.pk), agenda_objects)

    def test_proposal_appointment_is_returned_as_occupied_without_cache(self):
        Appointment.objects.create(
            related_property=Property.objects.first(),
            contact=Contact.objects.first(),
            agent=self.agent,
            appointment_type="proposal",
            date=date(2026, 8, 25),
            time=time(11, 0),
            end_time=time(11, 30),
            status="scheduled",
        )
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("available_slots"),
            {"date": "2026-08-25", "agent_id": self.agent.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("11:00", response.json()["occupied"])
        self.assertIn("no-cache", response.headers["Cache-Control"])

class AppointmentResultFlowAdditionalTests(TestCase):
    setUp = AppointmentResultFlowTests.setUp

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
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, "active")

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

    def test_manager_can_complete_an_agents_appointment_and_create_listing(self):
        manager = get_user_model().objects.create_user(
            username="manager",
            password="test-password",
            role="manager",
        )
        self.client.force_login(manager)

        comment_response = self.client.post(
            reverse("appointment_add_result", args=[self.appointment.pk]),
            {"result_comment": "Comentario añadido por el manager."},
        )

        self.appointment.refresh_from_db()
        self.assertRedirects(
            comment_response,
            reverse("appointment_detail", args=[self.appointment.pk]),
        )
        self.assertEqual(self.appointment.status, "completed")

        form_response = self.client.get(
            reverse("create_listing", args=[self.appointment.pk])
        )
        self.assertEqual(form_response.status_code, 200)

        create_response = self.client.post(
            reverse("create_listing", args=[self.appointment.pk]),
            {
                "owner": self.contact.pk,
                "start_date": "2026-08-11",
                "end_date": "2027-02-11",
                "commission_percent": "3.00",
            },
        )

        listing = Listing.objects.get()
        self.assertRedirects(
            create_response,
            reverse("listing_detail", args=[listing.pk]),
        )
        self.assertEqual(listing.agent, self.user)
