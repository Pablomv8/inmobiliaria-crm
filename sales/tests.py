from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from contacts.models import Contact
from properties.models import Property

from .forms import SaleForm
from .models import Sale


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

    def test_sale_form_commission_is_in_euros_and_accepts_more_than_one_hundred(self):
        field = SaleForm().fields["commission_amount"]

        self.assertEqual(field.label, "Comisión (€)")
        self.assertNotIn("max", field.widget.attrs)

# Create your tests here.
