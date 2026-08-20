from datetime import time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from calendar_app.models import Appointment
from contacts.models import Contact
from news.models import News
from orders.models import Order
from properties.models import Property
from users.models import User

from .forms import GoalForm
from .models import Goal
from .services import calculate_progress


class GoalTestMixin:
    def setUp(self):
        self.manager = User.objects.create_user(
            username="manager_goals",
            password="test-pass-123",
            role="manager",
        )
        self.agent = User.objects.create_user(
            username="agent_goals",
            password="test-pass-123",
            role="agent",
        )
        self.other_agent = User.objects.create_user(
            username="other_goals",
            password="test-pass-123",
            role="agent",
        )
        self.today = timezone.localdate()
        self.goal = Goal.objects.create(
            name="Dos noticias",
            scope=Goal.SCOPE_INDIVIDUAL,
            metric="news",
            target_count=2,
            start_date=self.today - timedelta(days=1),
            end_date=self.today + timedelta(days=5),
            created_by=self.manager,
        )
        self.goal.assignees.add(self.agent)
        self.property = Property.objects.create(
            street="Calle Objetivo",
            number="1",
            city="Madrid",
            property_type="flat",
        )


class GoalProgressTests(GoalTestMixin, TestCase):
    def test_progress_counts_only_records_from_assigned_agents(self):
        News.objects.create(
            related_property=self.property,
            agent=self.agent,
            motivation="sale",
            client_price=Decimal("200000"),
            estimated_price=Decimal("195000"),
        )
        News.objects.create(
            related_property=self.property,
            agent=self.other_agent,
            motivation="sale",
            client_price=Decimal("210000"),
            estimated_price=Decimal("205000"),
        )

        self.assertEqual(calculate_progress(self.goal), 1)

    def test_cancelled_sale_appointments_do_not_count(self):
        contact = Contact.objects.create(
            name="Cliente",
            phone="600000000",
            contact_type="buyer",
            assigned_agent=self.agent,
        )
        self.goal.metric = "sale_appointments"
        self.goal.save(update_fields=["metric"])
        Appointment.objects.create(
            related_property=self.property,
            contact=contact,
            agent=self.agent,
            appointment_type="sale",
            date=self.today,
            time=time(10, 0),
            end_time=time(11, 0),
            status="scheduled",
        )
        Appointment.objects.create(
            related_property=self.property,
            contact=contact,
            agent=self.agent,
            appointment_type="sale",
            date=self.today,
            time=time(12, 0),
            end_time=time(13, 0),
            status="cancelled",
        )

        self.assertEqual(calculate_progress(self.goal), 1)

    def test_order_progress_uses_order_creator_not_buyer_agent(self):
        buyer = Contact.objects.create(
            name="Compradora de otro responsable",
            phone="600000010",
            contact_type="buyer",
            assigned_agent=self.other_agent,
        )
        self.goal.metric = "orders"
        self.goal.save(update_fields=["metric"])
        Order.objects.create(
            buyer=buyer,
            agent=self.agent,
            operation_type="sale",
            max_price="250000",
            payment_type="financing",
            property_type="flat",
        )

        self.assertEqual(calculate_progress(self.goal), 1)


class GoalFormTests(GoalTestMixin, TestCase):
    def base_data(self):
        return {
            "name": "Objetivo válido",
            "description": "",
            "metric": "contacts",
            "target_count": 3,
            "start_date": self.today,
            "end_date": self.today + timedelta(days=10),
        }

    def test_individual_goal_requires_exactly_one_agent(self):
        data = {**self.base_data(), "scope": "individual", "assignees": []}
        form = GoalForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("exactamente un agente", form.errors["assignees"][0])

    def test_team_goal_requires_at_least_two_agents(self):
        data = {
            **self.base_data(),
            "scope": "team",
            "assignees": [self.agent.pk],
        }
        form = GoalForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("al menos dos agentes", form.errors["assignees"][0])


class GoalPermissionTests(GoalTestMixin, TestCase):
    def test_agent_sees_only_assigned_goals(self):
        hidden_goal = Goal.objects.create(
            name="Objetivo de otro agente",
            scope="individual",
            metric="contacts",
            target_count=1,
            start_date=self.today,
            end_date=self.today + timedelta(days=5),
            created_by=self.manager,
        )
        hidden_goal.assignees.add(self.other_agent)
        self.client.force_login(self.agent)

        response = self.client.get(reverse("goal_list"))

        self.assertContains(response, self.goal.name)
        self.assertNotContains(response, hidden_goal.name)

    def test_agent_can_open_assigned_goal_progress(self):
        self.client.force_login(self.agent)

        response = self.client.get(reverse("goal_detail", args=[self.goal.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.goal.name)
        self.assertContains(response, "Progreso total")

    def test_agent_cannot_create_edit_or_delete_goals(self):
        self.client.force_login(self.agent)

        self.assertEqual(self.client.get(reverse("goal_create")).status_code, 403)
        self.assertEqual(
            self.client.get(reverse("goal_update", args=[self.goal.pk])).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(reverse("goal_delete", args=[self.goal.pk])).status_code,
            403,
        )

    def test_manager_can_create_goal(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("goal_create"),
            {
                "name": "Objetivo del equipo",
                "description": "",
                "scope": "team",
                "metric": "listings",
                "target_count": 4,
                "start_date": self.today,
                "end_date": self.today + timedelta(days=20),
                "assignees": [self.agent.pk, self.other_agent.pk],
            },
        )

        created = Goal.objects.get(name="Objetivo del equipo")
        self.assertRedirects(response, reverse("goal_detail", args=[created.pk]))
        self.assertEqual(created.assignees.count(), 2)


class SeedGoalsCommandTests(GoalTestMixin, TestCase):
    def test_seed_command_is_idempotent(self):
        call_command("seed_goals", verbosity=0)
        first_count = Goal.objects.filter(name__startswith="[DEMO]").count()

        call_command("seed_goals", verbosity=0)

        self.assertEqual(first_count, 9)
        self.assertEqual(
            Goal.objects.filter(name__startswith="[DEMO]").count(),
            first_count,
        )
