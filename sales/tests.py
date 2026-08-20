from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from calendar_app.models import Appointment
from contacts.models import Contact
from listings.models import Listing
from orders.models import Order
from properties.models import Property

from .forms import SaleForm
from .models import RentalContract, Sale


class MonetaryCommissionTests(TestCase):
    def setUp(self):
        self.agent = get_user_model().objects.create_user(
            username="commission-agent",
            password="test-password",
        )
        self.buyer = Contact.objects.create(
            name="Compradora comisión",
            phone="600999001",
            contact_type="buyer",
        )
        self.property = Property.objects.create(
            street="Calle Comisión",
            number="12",
            city="Madrid",
            property_type="flat",
        )

    def test_sale_stores_the_agreed_commission_as_a_direct_amount(self):
        sale = Sale.objects.create(
            related_property=self.property,
            buyer=self.buyer,
            agent=self.agent,
            sale_price="250000.00",
            commission_amount="8750.00",
            sale_date=date(2026, 8, 15),
        )
        sale.refresh_from_db()

        self.assertEqual(sale.commission_amount, Decimal("8750.00"))

    def test_sale_form_commissions_are_in_euros_and_accept_more_than_one_hundred(self):
        form = SaleForm()

        self.assertEqual(
            form.fields["seller_commission"].label,
            "Comisión entregada por el vendedor (€)",
        )
        self.assertEqual(
            form.fields["buyer_commission"].label,
            "Comisión entregada por el comprador (€)",
        )
        self.assertNotIn("max", form.fields["seller_commission"].widget.attrs)


class ContractClosingFlowTests(TestCase):
    def setUp(self):
        self.agent = get_user_model().objects.create_user(
            username="closing-agent",
            password="test-password",
            role="agent",
        )
        self.owner = Contact.objects.create(
            name="Propietaria anterior",
            phone="600990001",
            contact_type="owner",
            assigned_agent=self.agent,
        )
        self.client_contact = Contact.objects.create(
            name="Cliente adquirente",
            phone="600990002",
            contact_type="buyer",
            assigned_agent=self.agent,
        )
        self.client.force_login(self.agent)

    def build_contract(self, operation_type):
        property_obj = Property.objects.create(
            street=f"Calle cierre {operation_type}",
            number="1",
            city="Madrid",
            property_type="flat",
        )
        property_obj.contacts.add(self.owner)
        listing = Listing.objects.create(
            property=property_obj,
            listing_type=operation_type,
            owner_price="250000" if operation_type == "sale" else "1200",
            agency_price="245000" if operation_type == "sale" else "1150",
            agreed_price="248000" if operation_type == "sale" else "1180",
            price_diference="5000" if operation_type == "sale" else "50",
            commission_amount="4500" if operation_type == "sale" else "1180",
            owner=self.owner,
            agent=self.agent,
        )
        order = Order.objects.create(
            buyer=self.client_contact,
            operation_type=operation_type,
            max_price="260000" if operation_type == "sale" else "1500",
            payment_type="financing" if operation_type == "sale" else "cash",
            property_type="flat",
        )
        appointment = Appointment.objects.create(
            related_property=property_obj,
            contact=self.client_contact,
            agent=self.agent,
            appointment_type="contract",
            date=date(2026, 8, 19),
            time=time(10, 0),
            end_time=time(11, 0),
            status="completed",
            result_comment="Las partes revisan el contrato.",
            listing=listing,
            order=order,
        )
        return property_obj, listing, order, appointment

    def test_signed_sale_transfers_ownership_and_keeps_full_history(self):
        property_obj, listing, order, appointment = self.build_contract("sale")

        decision_response = self.client.post(
            reverse("contract_signing_decision", args=[appointment.pk]),
            {"signed": "yes"},
        )
        self.assertRedirects(
            decision_response,
            reverse("create_closing_from_contract", args=[appointment.pk]),
        )

        response = self.client.post(
            reverse("create_closing_from_contract", args=[appointment.pk]),
            {
                "sale_price": "247000.00",
                "deposit_amount": "5000.00",
                "earnest_money_amount": "12000.00",
                "seller_commission": "4500.00",
                "buyer_commission": "1500.00",
                "contract_reference": "CV-2026-001",
                "notes": "Entrega de llaves incluida.",
            },
        )

        sale = Sale.objects.get()
        self.assertRedirects(response, reverse("sale_detail", args=[sale.pk]))
        self.assertEqual(sale.sale_date, timezone.localdate())
        self.assertEqual(sale.listing, listing)
        self.assertEqual(sale.source_contract_appointment, appointment)
        self.assertEqual(sale.former_owner, self.owner)
        self.assertEqual(sale.buyer, self.client_contact)
        self.assertEqual(sale.commission_amount, Decimal("6000.00"))
        self.assertEqual(sale.deposit_amount, Decimal("5000.00"))
        self.assertEqual(sale.earnest_money_amount, Decimal("12000.00"))

        listing.refresh_from_db()
        property_obj.refresh_from_db()
        order.refresh_from_db()
        appointment.refresh_from_db()
        self.client_contact.refresh_from_db()
        self.assertEqual(listing.status, "sold")
        self.assertEqual(listing.workflow_status, "closed")
        self.assertEqual(listing.owner, self.owner)
        self.assertEqual(property_obj.status, "sold")
        self.assertEqual(property_obj.occupied_by, "owner")
        self.assertFalse(property_obj.contacts.filter(pk=self.owner.pk).exists())
        self.assertTrue(
            property_obj.contacts.filter(pk=self.client_contact.pk).exists()
        )
        self.assertEqual(self.client_contact.contact_type, "owner")
        self.assertEqual(order.status, "closed")
        self.assertIs(appointment.result_success, True)

        detail_response = self.client.get(reverse("sale_detail", args=[sale.pk]))
        self.assertContains(detail_response, "Propietaria anterior")
        self.assertContains(detail_response, "Cliente adquirente")
        self.assertContains(detail_response, "CV-2026-001")
        list_response = self.client.get(reverse("sale_list"))
        self.assertContains(list_response, property_obj.full_address)
        self.assertContains(list_response, reverse("sale_detail", args=[sale.pk]))

    def test_signed_rental_keeps_owner_and_registers_tenant(self):
        property_obj, listing, order, appointment = self.build_contract("rent")
        self.client.post(
            reverse("contract_signing_decision", args=[appointment.pk]),
            {"signed": "yes"},
        )

        response = self.client.post(
            reverse("create_closing_from_contract", args=[appointment.pk]),
            {
                "rent_price": "1175.00",
                "deposit_amount": "2350.00",
                "earnest_money_amount": "500.00",
                "owner_commission": "1175.00",
                "tenant_commission": "600.00",
                "start_date": "2026-09-01",
                "end_date": "2027-08-31",
                "contract_reference": "ALQ-2026-001",
                "notes": "Duración inicial de un año.",
            },
        )

        contract = RentalContract.objects.get()
        self.assertRedirects(
            response,
            reverse("rental_contract_detail", args=[contract.pk]),
        )
        self.assertEqual(contract.contract_date, timezone.localdate())
        self.assertEqual(contract.owner, self.owner)
        self.assertEqual(contract.tenant, self.client_contact)
        self.assertEqual(contract.commission_amount, Decimal("1775.00"))

        listing.refresh_from_db()
        property_obj.refresh_from_db()
        order.refresh_from_db()
        self.client_contact.refresh_from_db()
        self.assertEqual(listing.status, "rented")
        self.assertEqual(listing.workflow_status, "closed")
        self.assertEqual(property_obj.status, "rented")
        self.assertEqual(property_obj.occupied_by, "tenants")
        self.assertTrue(property_obj.contacts.filter(pk=self.owner.pk).exists())
        self.assertTrue(
            property_obj.contacts.filter(pk=self.client_contact.pk).exists()
        )
        self.assertEqual(self.client_contact.contact_type, "buyer")
        self.assertEqual(order.status, "closed")
        list_response = self.client.get(reverse("rental_contract_list"))
        self.assertContains(list_response, property_obj.full_address)
        self.assertContains(
            list_response,
            reverse("rental_contract_detail", args=[contract.pk]),
        )

    def test_unsigned_contract_does_not_create_a_closing(self):
        _, _, _, appointment = self.build_contract("sale")

        response = self.client.post(
            reverse("contract_signing_decision", args=[appointment.pk]),
            {"signed": "no"},
        )

        self.assertRedirects(
            response,
            reverse("appointment_detail", args=[appointment.pk]),
        )
        appointment.refresh_from_db()
        self.assertIs(appointment.result_success, False)
        self.assertFalse(Sale.objects.exists())
        self.assertFalse(RentalContract.objects.exists())

    def test_manager_can_reassign_a_sale_and_a_rental_contract(self):
        manager = get_user_model().objects.create_user(
            username="closing-manager",
            password="test-password",
            role="manager",
        )
        new_agent = get_user_model().objects.create_user(
            username="closing-new-agent",
            password="test-password",
            role="agent",
        )
        sale_property, sale_listing, sale_order, sale_appointment = (
            self.build_contract("sale")
        )
        sale = Sale.objects.create(
            related_property=sale_property,
            buyer=self.client_contact,
            former_owner=self.owner,
            agent=self.agent,
            sale_price="247000",
            listing=sale_listing,
            order=sale_order,
            source_contract_appointment=sale_appointment,
            status="signed",
        )
        rental_property, rental_listing, rental_order, rental_appointment = (
            self.build_contract("rent")
        )
        rental = RentalContract.objects.create(
            related_property=rental_property,
            listing=rental_listing,
            order=rental_order,
            tenant=self.client_contact,
            owner=self.owner,
            agent=self.agent,
            source_contract_appointment=rental_appointment,
            rent_price="1175",
        )
        self.client.force_login(manager)

        sale_response = self.client.post(
            reverse("sale_reassign", args=[sale.pk]),
            {"agent": new_agent.pk},
        )
        rental_response = self.client.post(
            reverse("rental_contract_reassign", args=[rental.pk]),
            {"agent": new_agent.pk},
        )

        sale.refresh_from_db()
        rental.refresh_from_db()
        self.assertRedirects(
            sale_response,
            reverse("sale_detail", args=[sale.pk]),
        )
        self.assertRedirects(
            rental_response,
            reverse("rental_contract_detail", args=[rental.pk]),
        )
        self.assertEqual(sale.agent, new_agent)
        self.assertEqual(rental.agent, new_agent)

    def test_agent_cannot_use_the_sale_reassignment_endpoint(self):
        property_obj = Property.objects.create(
            street="Calle protegida",
            number="3",
            city="Madrid",
            property_type="flat",
        )
        sale = Sale.objects.create(
            related_property=property_obj,
            buyer=self.client_contact,
            agent=self.agent,
            sale_price="180000",
        )
        other_agent = get_user_model().objects.create_user(
            username="unauthorised-agent",
            password="test-password",
            role="agent",
        )

        response = self.client.post(
            reverse("sale_reassign", args=[sale.pk]),
            {"agent": other_agent.pk},
        )

        sale.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(sale.agent, self.agent)

# Create your tests here.
