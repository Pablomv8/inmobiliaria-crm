from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from properties.models import Zone

from .forms import TaskForm
from .models import Task


class TaskTypeFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            username="task-manager",
            password="test-password",
            role="manager",
        )
        self.agent = user_model.objects.create_user(
            username="task-agent",
            password="test-password",
            role="agent",
        )
        self.other_agent = user_model.objects.create_user(
            username="task-other-agent",
            password="test-password",
            role="agent",
        )
        self.zone = Zone.objects.create(name="Centro tareas")
        self.other_zone = Zone.objects.create(name="Norte tareas")
        self.client.force_login(self.manager)

    def test_custom_task_requires_name_description_and_assignee(self):
        response = self.client.post(
            reverse("task_create"),
            {
                "task_type": "custom",
                "title": "",
                "description": "",
                "assigned_to": "",
                "priority": "medium",
                "status": "pending",
                "due_date": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "title",
            "Escribe un nombre para la tarea personalizada.",
        )
        self.assertFormError(
            response.context["form"],
            "description",
            "Escribe una descripción para la tarea personalizada.",
        )
        self.assertFormError(
            response.context["form"],
            "assigned_to",
            "Selecciona la persona responsable de la tarea.",
        )
        self.assertFalse(Task.objects.exists())

    def test_custom_task_is_created_with_its_content_and_assignee(self):
        response = self.client.post(
            reverse("task_create"),
            {
                "task_type": "custom",
                "title": "Preparar dossier comercial",
                "description": "Recopilar fotografías y documentación.",
                "assigned_to": self.agent.pk,
                "priority": "high",
                "status": "pending",
                "due_date": "2026-08-20T12:30",
            },
        )

        self.assertRedirects(response, reverse("task_list"))
        task = Task.objects.get()
        self.assertEqual(task.task_type, "custom")
        self.assertEqual(task.title, "Preparar dossier comercial")
        self.assertEqual(
            task.description,
            "Recopilar fotografías y documentación.",
        )
        self.assertEqual(task.assigned_to, self.agent)
        self.assertEqual(task.created_by, self.manager)
        self.assertIsNone(task.zone)

    def test_zone_sweep_requires_zone_and_generates_its_name(self):
        invalid_response = self.client.post(
            reverse("task_create"),
            {
                "task_type": "zone_sweep",
                "zone": "",
                "assigned_to": self.agent.pk,
                "priority": "medium",
                "status": "pending",
                "due_date": "",
            },
        )

        self.assertEqual(invalid_response.status_code, 200)
        self.assertFormError(
            invalid_response.context["form"],
            "zone",
            "Selecciona la zona que se debe peinar.",
        )

        response = self.client.post(
            reverse("task_create"),
            {
                "task_type": "zone_sweep",
                "title": "Este nombre debe ignorarse",
                "description": "Este texto también debe ignorarse",
                "zone": self.zone.pk,
                "assigned_to": self.agent.pk,
                "priority": "medium",
                "status": "pending",
                "due_date": "",
            },
        )

        self.assertRedirects(response, reverse("task_list"))
        task = Task.objects.get()
        self.assertEqual(task.task_type, "zone_sweep")
        self.assertEqual(task.zone, self.zone)
        self.assertEqual(task.title, "Peinar zona Centro tareas")
        self.assertEqual(task.description, "")
        self.assertEqual(task.assigned_to, self.agent)

    def test_editing_can_change_custom_task_into_zone_sweep(self):
        task = Task.objects.create(
            task_type="custom",
            title="Tarea anterior",
            description="Descripción anterior",
            assigned_to=self.agent,
            created_by=self.manager,
        )

        response = self.client.post(
            reverse("task_update", args=[task.pk]),
            {
                "task_type": "zone_sweep",
                "zone": self.other_zone.pk,
                "assigned_to": self.other_agent.pk,
                "priority": "low",
                "status": "in_progress",
                "due_date": "",
            },
        )

        self.assertRedirects(response, reverse("task_list"))
        task.refresh_from_db()
        self.assertEqual(task.task_type, "zone_sweep")
        self.assertEqual(task.title, "Peinar zona Norte tareas")
        self.assertEqual(task.zone, self.other_zone)
        self.assertEqual(task.assigned_to, self.other_agent)

    def test_manager_can_filter_tasks_by_type_and_zone(self):
        custom_task = Task.objects.create(
            task_type="custom",
            title="Llamar a propietarios",
            description="Contactar la base de datos.",
            assigned_to=self.agent,
        )
        zone_task = Task.objects.create(
            task_type="zone_sweep",
            zone=self.zone,
            assigned_to=self.agent,
        )
        Task.objects.create(
            task_type="zone_sweep",
            zone=self.other_zone,
            assigned_to=self.other_agent,
        )

        response = self.client.get(
            reverse("task_list"),
            {"task_type": "zone_sweep", "zone": self.zone.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["tasks"], [zone_task])
        self.assertNotIn(custom_task, response.context["tasks"])
        self.assertContains(response, "Peinar zona Centro tareas")

    def test_agent_only_sees_tasks_assigned_to_them(self):
        own_task = Task.objects.create(
            task_type="custom",
            title="Mi tarea",
            description="Trabajo propio.",
            assigned_to=self.agent,
        )
        Task.objects.create(
            task_type="custom",
            title="Tarea ajena",
            description="Trabajo de otra persona.",
            assigned_to=self.other_agent,
        )
        self.client.force_login(self.agent)

        response = self.client.get(reverse("task_list"))

        self.assertQuerySetEqual(response.context["tasks"], [own_task])
        self.assertContains(response, "Mi tarea")
        self.assertNotContains(response, "Tarea ajena")

    def test_task_detail_displays_information_for_each_type(self):
        custom_task = Task.objects.create(
            task_type="custom",
            title="Revisar contrato",
            description="Comprobar todas las cláusulas.",
            assigned_to=self.agent,
        )
        zone_task = Task.objects.create(
            task_type="zone_sweep",
            zone=self.zone,
            assigned_to=self.agent,
        )

        custom_response = self.client.get(
            reverse("task_detail", args=[custom_task.pk])
        )
        zone_response = self.client.get(
            reverse("task_detail", args=[zone_task.pk])
        )

        self.assertContains(custom_response, "Descripción de la tarea")
        self.assertContains(custom_response, "Comprobar todas las cláusulas.")
        self.assertContains(zone_response, "Peinado comercial")
        self.assertContains(zone_response, self.zone.name)


class TaskFormModelValidationTests(TestCase):
    def test_form_exposes_only_the_new_task_fields(self):
        form = TaskForm()

        self.assertEqual(
            list(form.fields),
            [
                "task_type",
                "title",
                "description",
                "zone",
                "assigned_to",
                "priority",
                "due_date",
                "status",
            ],
        )
        self.assertNotIn("contact", form.fields)
        self.assertNotIn("related_property", form.fields)
