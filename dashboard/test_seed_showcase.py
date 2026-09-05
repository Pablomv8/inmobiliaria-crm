import io

from django.core.management import call_command
from django.test import TestCase

from calendar_app.models import Appointment
from contacts.models import Contact
from goals.models import Goal
from properties.models import Property
from sales.models import RentalContract, Sale
from tasks.models import Task
from users.models import User


class SeedShowcaseCommandTests(TestCase):
    user_password = "AgentShowcase!8472"
    admin_password = "AdminShowcase!9631"

    def run_seed(self, *extra_args):
        output = io.StringIO()
        call_command(
            "seed_showcase",
            *extra_args,
            user_password=self.user_password,
            admin_password=self.admin_password,
            stdout=output,
        )
        return output.getvalue()

    def test_creates_secure_integral_and_idempotent_showcase(self):
        output = self.run_seed()

        administrator = User.objects.get(username="admin_demo")
        manager = User.objects.get(username="pablo")
        self.assertTrue(administrator.is_superuser)
        self.assertTrue(administrator.is_staff)
        self.assertEqual(administrator.role, "admin")
        self.assertTrue(administrator.check_password(self.admin_password))
        self.assertEqual(manager.role, "manager")
        self.assertTrue(manager.check_password(self.user_password))
        self.assertTrue(
            User.objects.get(username="demo_flujo_integral").check_password(
                self.user_password
            )
        )
        self.assertNotIn("DemoCRM2026!", output)

        self.assertEqual(
            Property.objects.filter(
                city="Arcos de la Frontera",
                latitude__isnull=False,
                longitude__isnull=False,
            ).count(),
            3,
        )
        self.assertEqual(
            Appointment.objects.filter(appointment_type="financial_advice").count(),
            1,
        )
        self.assertEqual(Sale.objects.filter(contract_reference__startswith="CV-DEMO-").count(), 4)
        self.assertEqual(
            RentalContract.objects.filter(
                contract_reference__startswith="ALQ-DEMO-"
            ).count(),
            4,
        )
        self.assertEqual(Goal.objects.filter(name__startswith="[DEMO]").count(), 9)

        snapshot = {
            "users": User.objects.count(),
            "contacts": Contact.objects.count(),
            "properties": Property.objects.count(),
            "tasks": Task.objects.count(),
            "goals": Goal.objects.count(),
            "sales": Sale.objects.count(),
            "rentals": RentalContract.objects.count(),
        }
        self.run_seed()
        self.assertEqual(
            snapshot,
            {
                "users": User.objects.count(),
                "contacts": Contact.objects.count(),
                "properties": Property.objects.count(),
                "tasks": Task.objects.count(),
                "goals": Goal.objects.count(),
                "sales": Sale.objects.count(),
                "rentals": RentalContract.objects.count(),
            },
        )

    def test_purge_removes_only_showcase_records(self):
        unrelated = User.objects.create_user(
            username="usuario_real",
            password="UnrelatedPass!7412",
            role="agent",
        )
        self.run_seed()

        output = io.StringIO()
        call_command("seed_showcase", "--purge", stdout=output)

        self.assertTrue(User.objects.filter(pk=unrelated.pk).exists())
        self.assertFalse(User.objects.filter(username="admin_demo").exists())
        self.assertFalse(Contact.objects.filter(identification_number__startswith="DEMO-").exists())
        self.assertFalse(
            Property.objects.filter(description__startswith="[DEMO PRESENTACION]").exists()
        )
        self.assertFalse(Sale.objects.filter(contract_reference__startswith="CV-DEMO-").exists())
        self.assertFalse(
            RentalContract.objects.filter(
                contract_reference__startswith="ALQ-DEMO-"
            ).exists()
        )
        self.assertFalse(Goal.objects.filter(name__startswith="[DEMO]").exists())

