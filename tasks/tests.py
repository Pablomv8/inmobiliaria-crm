from django.contrib.auth import get_user_model
from datetime import date, datetime, time
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from properties.models import Zone
from properties.models import Property
from contacts.models import Contact
from calendar_app.models import Appointment

from .forms import TaskForm
from .models import Street, Task
from .scheduling import task_occurrences
from .street_import import parse_overpass_streets


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
        self.street = Street.objects.create(
            name="Calle Corredera",
            geometry={
                "type": "MultiLineString",
                "coordinates": [[[-5.81, 36.75], [-5.80, 36.76]]],
            },
            external_ids=[101],
        )
        self.other_street = Street.objects.create(
            name="Calle Matrera",
            geometry={
                "type": "MultiLineString",
                "coordinates": [[[-5.80, 36.75], [-5.79, 36.76]]],
            },
            external_ids=[102],
        )
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
                "schedule_date": "2026-08-21",
                "start_time": "09:00",
                "end_time": "11:00",
                "repeat_days": "3",
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
        self.assertEqual(task.schedule_date.isoformat(), "2026-08-21")
        self.assertEqual(task.start_time.strftime("%H:%M"), "09:00")
        self.assertEqual(task.end_time.strftime("%H:%M"), "11:00")
        self.assertEqual(task.repeat_days, 3)
        self.assertIsNone(task.due_date)

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
                "schedule_date": "2026-08-25",
                "start_time": "10:00",
                "end_time": "12:00",
                "repeat_days": "2",
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

    def test_zone_sweep_rejects_invalid_time_range(self):
        response = self.client.post(
            reverse("task_create"),
            {
                "task_type": "zone_sweep",
                "zone": self.zone.pk,
                "schedule_date": "2026-08-25",
                "start_time": "12:00",
                "end_time": "10:00",
                "repeat_days": "2",
                "assigned_to": self.agent.pk,
                "priority": "medium",
                "status": "pending",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "end_time",
            "La hora de fin debe ser posterior a la hora de inicio.",
        )

    def test_street_sweep_requires_streets_and_generates_its_name(self):
        invalid_response = self.client.post(
            reverse("task_create"),
            {
                "task_type": "street_sweep",
                "streets": [],
                "schedule_date": "2026-08-26",
                "start_time": "09:00",
                "end_time": "11:00",
                "repeat_days": "2",
                "assigned_to": self.agent.pk,
                "priority": "medium",
                "status": "pending",
            },
        )

        self.assertEqual(invalid_response.status_code, 200)
        self.assertFormError(
            invalid_response.context["form"],
            "streets",
            "Selecciona al menos una calle que se deba peinar.",
        )

        response = self.client.post(
            reverse("task_create"),
            {
                "task_type": "street_sweep",
                "streets": [self.street.pk, self.other_street.pk],
                "schedule_date": "2026-08-26",
                "start_time": "09:00",
                "end_time": "11:00",
                "repeat_days": "2",
                "assigned_to": self.agent.pk,
                "priority": "medium",
                "status": "pending",
            },
        )

        self.assertRedirects(response, reverse("task_list"))
        task = Task.objects.get()
        self.assertEqual(task.task_type, "street_sweep")
        self.assertEqual(
            task.title,
            "Peinar calles: Calle Corredera, Calle Matrera",
        )
        self.assertIsNone(task.zone)
        self.assertQuerySetEqual(
            task.streets.all(),
            [self.street, self.other_street],
        )
        self.assertEqual(len(task_occurrences(task)), 2)

    def test_street_sweep_form_renders_map_data(self):
        response = self.client.get(reverse("task_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mapa para seleccionar calles")
        self.assertContains(response, "Calle Corredera")
        self.assertContains(response, '"type": "FeatureCollection"')

    def test_task_form_rejects_schedule_conflicts(self):
        Task.objects.create(
            task_type="custom",
            title="Tarea ya programada",
            description="Ocupa una hora.",
            assigned_to=self.agent,
            due_date=timezone.make_aware(datetime(2026, 8, 28, 10, 0)),
        )

        response = self.client.post(
            reverse("task_create"),
            {
                "task_type": "custom",
                "title": "Tarea solapada",
                "description": "No debería poder guardarse.",
                "assigned_to": self.agent.pk,
                "priority": "medium",
                "status": "pending",
                "due_date": "2026-08-28T10:30",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "La persona asignada ya tiene otra cita, llamada o tarea en ese tramo horario.",
        )
        self.assertEqual(Task.objects.count(), 1)

    def test_task_form_respects_the_full_appointment_interval(self):
        property_obj = Property.objects.create(
            street="Calle Intervalo",
            number="3",
            city="Madrid",
            property_type="flat",
        )
        contact = Contact.objects.create(
            name="Contacto intervalo",
            phone="600555222",
            is_buyer=True,
        )
        Appointment.objects.create(
            related_property=property_obj,
            contact=contact,
            agent=self.agent,
            appointment_type="valuation",
            date=date(2026, 8, 29),
            time=time(10, 0),
            end_time=time(12, 0),
        )

        form = TaskForm(data={
            "task_type": "custom",
            "title": "Preparar visita",
            "description": "No debe solaparse con la cita larga.",
            "assigned_to": self.agent.pk,
            "priority": "medium",
            "status": "pending",
            "due_date": "2026-08-29T11:30",
        })

        self.assertFalse(form.is_valid())
        self.assertIn(
            "otra cita, llamada o tarea",
            form.non_field_errors()[0],
        )

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
        street_task = Task.objects.create(
            task_type="street_sweep",
            title="Peinar calles: Calle Corredera",
            assigned_to=self.agent,
        )
        street_task.streets.add(self.street)

        custom_response = self.client.get(
            reverse("task_detail", args=[custom_task.pk])
        )
        zone_response = self.client.get(
            reverse("task_detail", args=[zone_task.pk])
        )
        street_response = self.client.get(
            reverse("task_detail", args=[street_task.pk])
        )

        self.assertContains(custom_response, "Descripción de la tarea")
        self.assertContains(custom_response, "Comprobar todas las cláusulas.")
        self.assertContains(zone_response, "Peinado comercial")
        self.assertContains(zone_response, self.zone.name)
        self.assertContains(street_response, "Calles seleccionadas")
        self.assertContains(street_response, self.street.name)


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
                "streets",
                "assigned_to",
                "priority",
                "due_date",
                "schedule_date",
                "start_time",
                "end_time",
                "repeat_days",
                "status",
            ],
        )
        self.assertNotIn("contact", form.fields)
        self.assertNotIn("related_property", form.fields)


class StreetImportTests(TestCase):
    def test_bundled_arcos_snapshot_can_be_imported_idempotently(self):
        snapshot = Path(settings.BASE_DIR) / "tasks" / "data" / "arcos_streets.json"
        first_output = StringIO()
        second_output = StringIO()

        call_command(
            "import_arcos_streets",
            "--file",
            str(snapshot),
            stdout=first_output,
        )
        imported_count = Street.objects.filter(
            municipality="Arcos de la Frontera",
        ).count()
        call_command(
            "import_arcos_streets",
            "--file",
            str(snapshot),
            stdout=second_output,
        )

        self.assertGreaterEqual(imported_count, 500)
        self.assertEqual(
            Street.objects.filter(municipality="Arcos de la Frontera").count(),
            imported_count,
        )
        self.assertFalse(
            Street.objects.filter(
                municipality="Arcos de la Frontera",
                geometry={},
            ).exists()
        )
        self.assertIn(f"{imported_count} nuevas", first_output.getvalue())
        self.assertIn(f"{imported_count} actualizadas", second_output.getvalue())

    def test_parser_groups_segments_with_the_same_street_name(self):
        rows = parse_overpass_streets({
            "elements": [
                {
                    "id": 10,
                    "tags": {"name": "Calle Corredera"},
                    "geometry": [
                        {"lat": 36.75, "lon": -5.81},
                        {"lat": 36.76, "lon": -5.80},
                    ],
                },
                {
                    "id": 11,
                    "tags": {"name": "  CALLE corredera  "},
                    "geometry": [
                        {"lat": 36.76, "lon": -5.80},
                        {"lat": 36.77, "lon": -5.79},
                    ],
                },
                {
                    "id": 12,
                    "tags": {},
                    "geometry": [
                        {"lat": 36.76, "lon": -5.80},
                        {"lat": 36.77, "lon": -5.79},
                    ],
                },
            ],
        })

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Calle Corredera")
        self.assertEqual(rows[0]["external_ids"], [10, 11])
        self.assertEqual(rows[0]["geometry"]["type"], "MultiLineString")
        self.assertEqual(len(rows[0]["geometry"]["coordinates"]), 2)
