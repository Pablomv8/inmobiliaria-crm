from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from contacts.models import Contact
from listings.models import Listing
from news.models import News, NewsComment
from orders.models import Order
from properties.models import (
    Property,
    PropertyComment,
    PropertyStatusHistory,
    Zone,
)
from sales.models import RentalContract, Sale

from .models import (
    Appointment,
    Call,
    CallComment,
    CounterOffer,
    ProposalAppointment,
)


class FullWorkflowStateIntegrationTests(TestCase):
    def setUp(self):
        self.agent = get_user_model().objects.create_user(
            username="workflow-state-agent",
            password="test-password",
            role="agent",
        )
        self.zone = Zone.objects.create(name="Zona flujo integral")
        self.owner = Contact.objects.create(
            name="Propietaria flujo",
            phone="611000001",
            is_owner=True,
            assigned_agent=self.agent,
        )
        self.buyer = Contact.objects.create(
            name="Comprador flujo",
            phone="611000002",
            is_buyer=True,
            assigned_agent=self.agent,
        )
        self.client.force_login(self.agent)

    def create_property(self, suffix="venta"):
        property_obj = Property.objects.create(
            street=f"Calle Flujo {suffix}",
            number="1",
            city="Arcos de la Frontera",
            postal_code="11630",
            property_type="house",
            zone=self.zone,
            occupied_by="owner",
            created_by=self.agent,
        )
        self.owner.properties.add(property_obj)
        return property_obj

    def assert_states(
        self,
        *,
        listing=None,
        order=None,
        proposal=None,
        listing_workflow=None,
        order_status=None,
        proposal_status=None,
    ):
        if listing is not None:
            listing.refresh_from_db()
            self.assertEqual(listing.workflow_status, listing_workflow)
        if order is not None:
            order.refresh_from_db()
            self.assertEqual(order.status, order_status)
        if proposal is not None:
            proposal.refresh_from_db()
            self.assertEqual(proposal.status, proposal_status)

    def test_property_status_priority_covers_the_complete_lifecycle(self):
        property_obj = self.create_property("estados")
        self.assertEqual(property_obj.status, "never_contacted")

        comment = PropertyComment.objects.create(
            property=property_obj,
            user=self.agent,
            text="Primer contacto con la propiedad.",
        )
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.status, "contacted")

        PropertyComment.objects.filter(pk=comment.pk).update(
            created_at=timezone.now() - timedelta(days=31),
        )
        Property.refresh_aged_contact_statuses()
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.status, "contacted_30")

        property_obj.occupied_by = "vacant"
        property_obj.save()
        self.assertEqual(property_obj.status, "vacant")

        property_obj.occupied_by = "tenants"
        property_obj.save()
        self.assertEqual(property_obj.status, "rented")

        property_obj.occupied_by = "owner"
        property_obj.save()
        self.assertEqual(property_obj.status, "contacted_30")

        news = News.objects.create(
            related_property=property_obj,
            agent=self.agent,
            motivation="sale",
            client_price="250000",
            estimated_price="245000",
        )
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.status, "news")

        listing = Listing.objects.create(
            property=property_obj,
            owner=self.owner,
            agent=self.agent,
            listing_type="sale",
            owner_price="250000",
            agency_price="245000",
            agreed_price="247000",
            price_diference="5000",
            commission_amount="8000",
        )
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.status, "in_listing")

        listing.status = "rented"
        listing.save(update_fields=["status"])
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.status, "rented")

        listing.status = "sold"
        listing.save(update_fields=["status"])
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.status, "sold")

        listing.status = "cancelled"
        listing.save(update_fields=["status"])
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.status, "news")

        news.delete()
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.status, "contacted_30")
        self.assertTrue(
            PropertyStatusHistory.objects.filter(property=property_obj).exists()
        )

    def test_complete_sale_flow_keeps_every_related_status_in_sync(self):
        property_obj = self.create_property()
        news = News.objects.create(
            related_property=property_obj,
            agent=self.agent,
            motivation="sale",
            client_price="250000",
            estimated_price="245000",
        )
        self.assertEqual(property_obj.sync_status(), "news")
        self.assertEqual(news.status, "new")

        NewsComment.objects.create(
            news=news,
            user=self.agent,
            text="La propietaria confirma interés en vender.",
        )
        news.refresh_from_db()
        self.assertEqual(news.status, "contacted")

        acquisition = Appointment.objects.create(
            related_property=property_obj,
            contact=self.owner,
            agent=self.agent,
            appointment_type="acquisition",
            date=date(2027, 1, 10),
            time=time(9, 0),
            end_time=time(10, 0),
            news=news,
        )
        news.refresh_from_db()
        self.assertEqual(news.status, "appointment")

        acquisition.status = "completed"
        acquisition.result_comment = "La propietaria acepta trabajar con la agencia."
        acquisition.save(update_fields=["status", "result_comment"])
        news.refresh_from_db()
        self.assertEqual(news.status, "contacted")

        call = Call.objects.create(
            contact=self.owner,
            agent=self.agent,
            date=date(2027, 1, 11),
            time=time(9, 0),
            news=news,
        )
        news.refresh_from_db()
        self.assertEqual(news.status, "follow_up")
        CallComment.objects.create(
            call=call,
            user=self.agent,
            text="Se confirman los datos del encargo.",
        )
        self.client.post(
            reverse("call_update_status", args=[call.pk, "completed"]),
        )
        news.refresh_from_db()
        self.assertEqual(news.status, "contacted")

        listing = Listing.objects.create(
            property=property_obj,
            owner=self.owner,
            agent=self.agent,
            listing_type="sale",
            owner_price="250000",
            agency_price="245000",
            agreed_price="247000",
            price_diference="5000",
            commission_amount="8000",
            start_date=date(2027, 1, 12),
            end_date=date(2027, 7, 12),
            source_appointment=acquisition,
        )
        news.refresh_from_db()
        property_obj.refresh_from_db()
        self.assertEqual(news.status, "closed")
        self.assertEqual(property_obj.status, "in_listing")
        self.assertEqual(listing.workflow_status, "active")

        follow_up = Appointment.objects.create(
            related_property=property_obj,
            contact=self.owner,
            agent=self.agent,
            appointment_type="follow_up",
            date=date(2027, 1, 15),
            time=time(10, 0),
            end_time=time(11, 0),
            listing=listing,
        )
        self.assert_states(listing=listing, listing_workflow="follow_up_appointment")
        follow_up.status = "completed"
        follow_up.result_comment = "El encargo sigue correctamente."
        follow_up.save(update_fields=["status", "result_comment"])
        self.assert_states(listing=listing, listing_workflow="active")

        order = Order.objects.create(
            buyer=self.buyer,
            agent=self.agent,
            operation_type="sale",
            zone=self.zone,
            max_price="260000",
            payment_type="financing",
            property_type="house",
        )
        self.assertEqual(order.status, "active")

        sale_visit = Appointment.objects.create(
            related_property=property_obj,
            contact=self.buyer,
            agent=self.agent,
            appointment_type="sale",
            date=date(2027, 1, 20),
            time=time(11, 0),
            end_time=time(12, 0),
            listing=listing,
            order=order,
        )
        self.assert_states(
            listing=listing,
            order=order,
            listing_workflow="sale_appointment",
            order_status="sale_appointment",
        )
        sale_visit.status = "completed"
        sale_visit.result_comment = "El comprador quiere presentar una oferta."
        sale_visit.result_success = True
        sale_visit.save(
            update_fields=["status", "result_comment", "result_success"],
        )
        self.assert_states(
            listing=listing,
            order=order,
            listing_workflow="active",
            order_status="active",
        )

        proposal_meeting = Appointment.objects.create(
            related_property=property_obj,
            contact=self.buyer,
            agent=self.agent,
            appointment_type="proposal",
            date=date(2027, 1, 21),
            time=time(12, 0),
            end_time=time(13, 0),
            listing=listing,
            order=order,
            source_sale_appointment=sale_visit,
        )
        self.assert_states(
            listing=listing,
            order=order,
            listing_workflow="proposal_appointment",
            order_status="proposal_appointment",
        )
        proposal_meeting.status = "completed"
        proposal_meeting.result_comment = "Se registra la primera oferta."
        proposal_meeting.save(update_fields=["status", "result_comment"])
        proposal = ProposalAppointment.objects.create(
            source_sale_appointment=proposal_meeting,
            order=order,
            listing=listing,
            buyer=self.buyer,
            agent=self.agent,
            listing_price="247000",
            offered_price="238000",
            deposit_amount="5000",
            proposal_date=date(2027, 1, 21),
            end_date=date(2027, 1, 28),
        )
        self.assert_states(
            listing=listing,
            order=order,
            proposal=proposal,
            listing_workflow="proposal",
            order_status="proposal",
            proposal_status="submitted",
        )

        acceptance = Appointment.objects.create(
            related_property=property_obj,
            contact=self.owner,
            agent=self.agent,
            appointment_type="proposal_acceptance",
            date=date(2027, 1, 22),
            time=time(13, 0),
            end_time=time(14, 0),
            listing=listing,
            order=order,
            purchase_proposal=proposal,
        )
        self.assert_states(
            listing=listing,
            order=order,
            proposal=proposal,
            listing_workflow="acceptance_appointment",
            order_status="acceptance_appointment",
            proposal_status="acceptance_appointment",
        )
        acceptance.status = "completed"
        acceptance.result_comment = "La propietaria solicita una mejora."
        acceptance.save(update_fields=["status", "result_comment"])
        counteroffer = CounterOffer.objects.create(
            proposal=proposal,
            source_acceptance_appointment=acceptance,
            counteroffer_date=date(2027, 1, 22),
            owner_price="244000",
            notes="Precio mínimo aceptado por la propiedad.",
        )
        acceptance.result_success = False
        acceptance.save(update_fields=["result_success"])
        self.assert_states(
            listing=listing,
            order=order,
            proposal=proposal,
            listing_workflow="counteroffer",
            order_status="counteroffer",
            proposal_status="counteroffer",
        )

        response_meeting = Appointment.objects.create(
            related_property=property_obj,
            contact=self.buyer,
            agent=self.agent,
            appointment_type="proposal",
            date=date(2027, 1, 23),
            time=time(14, 0),
            end_time=time(15, 0),
            listing=listing,
            order=order,
            source_counteroffer=counteroffer,
        )
        self.assert_states(
            listing=listing,
            order=order,
            listing_workflow="proposal_appointment",
            order_status="proposal_appointment",
        )
        response_meeting.status = "completed"
        response_meeting.result_comment = "El comprador mejora la oferta."
        response_meeting.save(update_fields=["status", "result_comment"])
        final_proposal = ProposalAppointment.objects.create(
            source_sale_appointment=response_meeting,
            order=order,
            listing=listing,
            buyer=self.buyer,
            agent=self.agent,
            listing_price="247000",
            offered_price="244000",
            deposit_amount="6000",
            proposal_date=date(2027, 1, 23),
            end_date=date(2027, 1, 30),
        )
        self.assert_states(
            listing=listing,
            order=order,
            proposal=final_proposal,
            listing_workflow="proposal",
            order_status="proposal",
            proposal_status="submitted",
        )

        final_acceptance = Appointment.objects.create(
            related_property=property_obj,
            contact=self.owner,
            agent=self.agent,
            appointment_type="proposal_acceptance",
            date=date(2027, 1, 24),
            time=time(15, 0),
            end_time=time(16, 0),
            listing=listing,
            order=order,
            purchase_proposal=final_proposal,
        )
        self.assert_states(
            listing=listing,
            order=order,
            proposal=final_proposal,
            listing_workflow="acceptance_appointment",
            order_status="acceptance_appointment",
            proposal_status="acceptance_appointment",
        )
        final_acceptance.status = "completed"
        final_acceptance.result_comment = "Oferta aceptada."
        final_acceptance.result_success = True
        final_acceptance.save(
            update_fields=["status", "result_comment", "result_success"],
        )
        final_proposal.refresh_from_db()
        self.assertEqual(final_proposal.status, "accepted")

        contract = Appointment.objects.create(
            related_property=property_obj,
            contact=self.buyer,
            agent=self.agent,
            appointment_type="contract",
            date=date(2027, 1, 25),
            time=time(16, 0),
            end_time=time(17, 0),
            listing=listing,
            order=order,
            purchase_proposal=final_proposal,
            source_acceptance_appointment=final_acceptance,
        )
        self.assert_states(
            listing=listing,
            order=order,
            proposal=final_proposal,
            listing_workflow="contract_appointment",
            order_status="contract_appointment",
            proposal_status="contract_appointment",
        )
        signing = Appointment.objects.create(
            related_property=property_obj,
            contact=self.buyer,
            agent=self.agent,
            appointment_type="signing",
            date=date(2027, 1, 26),
            time=time(9, 0),
            end_time=time(10, 0),
            listing=listing,
            order=order,
            purchase_proposal=final_proposal,
            source_acceptance_appointment=final_acceptance,
        )
        self.assert_states(
            listing=listing,
            order=order,
            proposal=final_proposal,
            listing_workflow="signing_appointment",
            order_status="signing_appointment",
            proposal_status="signing_appointment",
        )
        signing.status = "cancelled"
        signing.save(update_fields=["status"])
        self.assert_states(
            listing=listing,
            order=order,
            proposal=final_proposal,
            listing_workflow="contract_appointment",
            order_status="contract_appointment",
            proposal_status="contract_appointment",
        )

        contract.status = "completed"
        contract.result_comment = "Contrato revisado y firmado por las partes."
        contract.save(update_fields=["status", "result_comment"])
        decision_response = self.client.post(
            reverse("contract_signing_decision", args=[contract.pk]),
            {"signed": "yes"},
        )
        self.assertRedirects(
            decision_response,
            reverse("create_closing_from_contract", args=[contract.pk]),
        )
        close_response = self.client.post(
            reverse("create_closing_from_contract", args=[contract.pk]),
            {
                "sale_price": "244000",
                "deposit_amount": "6000",
                "earnest_money_amount": "12000",
                "seller_commission": "7000",
                "buyer_commission": "1500",
                "contract_reference": "",
                "notes": "Cierre completo del flujo de prueba.",
            },
        )
        sale = Sale.objects.get()
        self.assertRedirects(close_response, reverse("sale_detail", args=[sale.pk]))

        listing.refresh_from_db()
        order.refresh_from_db()
        property_obj.refresh_from_db()
        news.refresh_from_db()
        self.buyer.refresh_from_db()
        self.assertEqual(listing.status, "sold")
        self.assertEqual(listing.workflow_status, "closed")
        self.assertEqual(order.status, "closed")
        self.assertEqual(property_obj.status, "sold")
        self.assertEqual(property_obj.occupied_by, "owner")
        self.assertEqual(news.status, "closed")
        self.assertTrue(self.buyer.is_owner)
        self.assertTrue(self.buyer.is_buyer)
        self.assertTrue(property_obj.contacts.filter(pk=self.buyer.pk).exists())
        self.assertFalse(property_obj.contacts.filter(pk=self.owner.pk).exists())
        self.assertEqual(sale.former_owner, self.owner)
        self.assertEqual(sale.commission_amount, 8500)

    def test_rental_closing_marks_listing_order_and_property_as_rented(self):
        property_obj = self.create_property("alquiler")
        listing = Listing.objects.create(
            property=property_obj,
            owner=self.owner,
            agent=self.agent,
            listing_type="rent",
            owner_price="1200",
            agency_price="1150",
            agreed_price="1180",
            price_diference="50",
            commission_amount="1180",
        )
        order = Order.objects.create(
            buyer=self.buyer,
            agent=self.agent,
            operation_type="rent",
            zone=self.zone,
            max_price="1400",
            payment_type="cash",
            property_type="house",
        )
        contract = Appointment.objects.create(
            related_property=property_obj,
            contact=self.buyer,
            agent=self.agent,
            appointment_type="contract",
            date=date(2027, 2, 1),
            time=time(10, 0),
            end_time=time(11, 0),
            listing=listing,
            order=order,
            status="completed",
            result_comment="Contrato de alquiler firmado.",
            result_success=True,
        )

        response = self.client.post(
            reverse("create_closing_from_contract", args=[contract.pk]),
            {
                "rent_price": "1180",
                "deposit_amount": "2360",
                "earnest_money_amount": "500",
                "owner_commission": "1180",
                "tenant_commission": "600",
                "start_date": "2027-02-01",
                "end_date": "2028-01-31",
                "contract_reference": "",
                "notes": "Alquiler anual.",
            },
        )
        rental = RentalContract.objects.get()
        self.assertRedirects(
            response,
            reverse("rental_contract_detail", args=[rental.pk]),
        )
        listing.refresh_from_db()
        order.refresh_from_db()
        property_obj.refresh_from_db()
        self.assertEqual(listing.status, "rented")
        self.assertEqual(listing.workflow_status, "closed")
        self.assertEqual(order.status, "closed")
        self.assertEqual(property_obj.status, "rented")
        self.assertEqual(property_obj.occupied_by, "tenants")
        self.assertTrue(property_obj.contacts.filter(pk=self.owner.pk).exists())
        self.assertTrue(property_obj.contacts.filter(pk=self.buyer.pk).exists())
