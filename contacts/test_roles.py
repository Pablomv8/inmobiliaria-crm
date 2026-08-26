from django.test import TestCase

from .models import Contact


class ContactIndependentRoleTests(TestCase):
    def test_contact_can_be_owner(self):
        contact = Contact.objects.create(
            name="Propietaria",
            phone="611100001",
            is_owner=True,
        )

        self.assertTrue(contact.is_owner)
        self.assertFalse(contact.is_buyer)
        self.assertEqual(contact.get_roles_display(), "Propietario")

    def test_contact_can_be_buyer(self):
        contact = Contact.objects.create(
            name="Comprador",
            phone="611100002",
            is_buyer=True,
        )

        self.assertFalse(contact.is_owner)
        self.assertTrue(contact.is_buyer)
        self.assertEqual(contact.get_roles_display(), "Comprador")

    def test_contact_can_be_owner_and_buyer_at_the_same_time(self):
        contact = Contact.objects.create(
            name="Cliente con ambos roles",
            phone="611100003",
            is_owner=True,
            is_buyer=True,
        )

        self.assertEqual(
            contact.get_roles_display(),
            "Propietario y comprador",
        )
