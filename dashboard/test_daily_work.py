from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from calendar_app.models import Appointment, Call
from contacts.models import Contact
from tasks.models import Task


class DailyWorkTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.agent = User.objects.create_user(
            username="daily-agent",
            password="test-password",
            role="agent",
            first_name="Ana",
        )
        self.other_agent = User.objects.create_user(
            username="daily-other",
            password="test-password",
            role="agent",
            first_name="Bruno",
        )
        self.manager = User.objects.create_user(
            username="daily-manager",
            password="test-password",
            role="manager",
        )
        self.contact = Contact.objects.create(
            name="Cliente jornada",
            last_name="Uno",
            identification_number="12345678Z",
            phone="600100200",
            marital_status="single",
            is_buyer=True,
            assigned_agent=self.agent,
        )
        self.other_contact = Contact.objects.create(
            name="Cliente jornada",
            last_name="Dos",
            identification_number="12345679S",
            phone="600100201",
            marital_status="single",
            is_buyer=True,
            assigned_agent=self.other_agent,
        )

    def create_appointment(self, agent, contact, **kwargs):
        values = {
            "contact": contact,
            "agent": agent,
            "appointment_type": "valuation",
            "date": timezone.localdate(),
            "time": time(10, 0),
            "end_time": time(11, 0),
        }
        values.update(kwargs)
        return Appointment.objects.create(**values)

    def test_agent_sees_only_their_activity_for_today(self):
        own_appointment = self.create_appointment(self.agent, self.contact)
        own_call = Call.objects.create(
            contact=self.contact,
            agent=self.agent,
            date=timezone.localdate(),
            time=time(12, 0),
        )
        own_task = Task.objects.create(
            task_type="custom",
            title="Preparar visita",
            description="Revisar la documentación",
            assigned_to=self.agent,
            created_by=self.manager,
            due_date=timezone.now() + timedelta(minutes=30),
        )
        other_appointment = self.create_appointment(
            self.other_agent,
            self.other_contact,
            time=time(13, 0),
            end_time=time(14, 0),
        )
        self.client.force_login(self.agent)

        response = self.client.get(reverse("daily_work"))

        self.assertEqual(response.status_code, 200)
        keys = {item.key for item in response.context["timeline"]}
        self.assertEqual(
            keys,
            {
                f"appointment-{own_appointment.pk}",
                f"call-{own_call.pk}",
                f"task-{own_task.pk}",
            },
        )
        self.assertNotIn(f"appointment-{other_appointment.pk}", keys)
        self.assertContains(response, reverse("appointment_detail", args=[own_appointment.pk]))
        self.assertContains(response, reverse("call_detail", args=[own_call.pk]))
        self.assertContains(response, reverse("task_detail", args=[own_task.pk]))

    def test_completed_activity_is_counted_but_not_left_pending(self):
        completed_appointment = self.create_appointment(
            self.agent,
            self.contact,
            status="completed",
            result_comment="Visita terminada.",
        )
        Call.objects.create(
            contact=self.contact,
            agent=self.agent,
            date=timezone.localdate(),
            time=time(12, 0),
            status="completed",
        )
        Task.objects.create(
            task_type="custom",
            title="Tarea terminada",
            description="Trabajo hecho",
            assigned_to=self.agent,
            created_by=self.manager,
            due_date=timezone.now(),
            status="done",
            completed_at=timezone.now(),
        )
        self.client.force_login(self.agent)

        response = self.client.get(reverse("daily_work"))

        self.assertEqual(response.context["completed_today"], 3)
        self.assertNotIn(
            f"appointment-{completed_appointment.pk}",
            {item.key for item in response.context["timeline"]},
        )

    def test_overdue_tasks_and_workflow_decisions_are_separated(self):
        overdue_task = Task.objects.create(
            task_type="custom",
            title="Documentación atrasada",
            description="Solicitar la documentación al cliente",
            assigned_to=self.agent,
            created_by=self.manager,
            due_date=timezone.now() - timedelta(days=1),
        )
        acquisition = self.create_appointment(
            self.agent,
            self.contact,
            appointment_type="acquisition",
            date=timezone.localdate() - timedelta(days=1),
            status="completed",
            result_comment="Cita finalizada.",
        )
        self.client.force_login(self.agent)

        response = self.client.get(reverse("daily_work"))

        self.assertEqual(list(response.context["overdue_tasks"]), [overdue_task])
        self.assertEqual(response.context["overdue_count"], 1)
        self.assertIn(
            f"workflow-appointment-{acquisition.pk}",
            {item.key for item in response.context["decisions"]},
        )
        self.assertEqual(response.context["decision_count"], 1)

    def test_manager_can_choose_a_worker_but_agent_cannot(self):
        own_appointment = self.create_appointment(self.agent, self.contact)
        other_appointment = self.create_appointment(
            self.other_agent,
            self.other_contact,
            time=time(13, 0),
            end_time=time(14, 0),
        )
        self.client.force_login(self.manager)

        manager_response = self.client.get(
            reverse("daily_work"),
            {"agent": self.other_agent.pk},
        )

        self.assertEqual(manager_response.context["selected_user"], self.other_agent)
        manager_keys = {item.key for item in manager_response.context["timeline"]}
        self.assertIn(f"appointment-{other_appointment.pk}", manager_keys)
        self.assertNotIn(f"appointment-{own_appointment.pk}", manager_keys)

        self.client.force_login(self.agent)
        agent_response = self.client.get(
            reverse("daily_work"),
            {"agent": self.other_agent.pk},
        )
        self.assertEqual(agent_response.context["selected_user"], self.agent)
        agent_keys = {item.key for item in agent_response.context["timeline"]}
        self.assertIn(f"appointment-{own_appointment.pk}", agent_keys)
        self.assertNotIn(f"appointment-{other_appointment.pk}", agent_keys)

    def test_daily_work_requires_authentication(self):
        response = self.client.get(reverse("daily_work"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('daily_work')}",
        )
