from django import forms
from django.contrib.auth import get_user_model
from config.widgets import CRMDateInput, CRMDateTimeInput, CRMTimeInput

from properties.models import Zone

from .models import Street, Task
from .scheduling import (
    ACTIVE_TASK_STATUSES,
    build_occurrences,
    schedule_has_conflict,
)
from users.permissions import can_manage_assignments


INPUT_CLASS = (
    "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 "
    "text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none "
    "focus:ring-4 focus:ring-indigo-100"
)


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
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
        ]
        labels = {
            "task_type": "Tipo de tarea",
            "title": "Nombre de la tarea",
            "description": "Descripción",
            "zone": "Zona que se debe peinar",
            "streets": "Calles que se deben peinar",
            "assigned_to": "Persona asignada",
            "priority": "Prioridad",
            "due_date": "Fecha límite",
            "schedule_date": "Fecha de inicio",
            "start_time": "Hora de inicio",
            "end_time": "Hora de fin",
            "repeat_days": "Número de días consecutivos",
            "status": "Estado",
        }
        widgets = {
            "task_type": forms.RadioSelect,
            "title": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Ej. Preparar documentación del inmueble",
            }),
            "description": forms.Textarea(attrs={
                "class": INPUT_CLASS,
                "rows": 4,
                "placeholder": "Describe qué debe hacerse y cualquier indicación importante.",
            }),
            "zone": forms.Select(attrs={"class": INPUT_CLASS}),
            "streets": forms.CheckboxSelectMultiple,
            "assigned_to": forms.Select(attrs={"class": INPUT_CLASS}),
            "priority": forms.Select(attrs={"class": INPUT_CLASS}),
            "due_date": CRMDateTimeInput(
                attrs={"class": INPUT_CLASS, "type": "datetime-local"},
            ),
            "schedule_date": CRMDateInput(
                attrs={"class": INPUT_CLASS, "type": "date"},
            ),
            "start_time": CRMTimeInput(
                attrs={"class": INPUT_CLASS, "type": "time", "step": "1800"},
            ),
            "end_time": CRMTimeInput(
                attrs={"class": INPUT_CLASS, "type": "time", "step": "1800"},
            ),
            "repeat_days": forms.Select(attrs={"class": INPUT_CLASS}),
            "status": forms.Select(attrs={"class": INPUT_CLASS}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].required = False
        self.fields["description"].required = False
        self.fields["zone"].required = False
        self.fields["streets"].required = False
        self.fields["assigned_to"].required = True
        self.fields["assigned_to"].error_messages["required"] = (
            "Selecciona la persona responsable de la tarea."
        )
        self.fields["assigned_to"].queryset = (
            get_user_model().objects.filter(is_active=True).order_by(
                "first_name",
                "last_name",
                "username",
            )
        )
        if user is not None and not can_manage_assignments(user):
            self.fields["assigned_to"].queryset = get_user_model().objects.filter(
                pk=user.pk,
                is_active=True,
            )
            self.fields["assigned_to"].initial = user
            self.fields["assigned_to"].widget = forms.HiddenInput()
        self.fields["zone"].queryset = Zone.objects.all().order_by("name")
        self.fields["streets"].queryset = Street.objects.filter(
            municipality="Arcos de la Frontera",
        ).order_by("name")
        self.fields["due_date"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["schedule_date"].required = False
        self.fields["start_time"].required = False
        self.fields["end_time"].required = False
        self.fields["repeat_days"].required = False
        self.fields["repeat_days"].widget.choices = [
            ("", "Selecciona la duración"),
            *[
                (days, "1 día" if days == 1 else f"{days} días")
                for days in range(1, 31)
            ],
        ]

    def clean(self):
        cleaned_data = super().clean()
        task_type = cleaned_data.get("task_type")
        zone = cleaned_data.get("zone")
        streets = cleaned_data.get("streets")

        if task_type == "custom":
            cleaned_data["zone"] = None
            cleaned_data["streets"] = Street.objects.none()
            cleaned_data["schedule_date"] = None
            cleaned_data["start_time"] = None
            cleaned_data["end_time"] = None
            cleaned_data["repeat_days"] = None
        elif task_type == "zone_sweep":
            if zone is not None:
                cleaned_data["title"] = f"Peinar zona {zone.name}"
            cleaned_data["streets"] = Street.objects.none()
            cleaned_data["description"] = ""
            cleaned_data["due_date"] = None
        elif task_type == "street_sweep":
            cleaned_data["zone"] = None
            if not streets:
                self.add_error(
                    "streets",
                    "Selecciona al menos una calle que se deba peinar.",
                )
            cleaned_data["description"] = ""
            cleaned_data["due_date"] = None

        occurrences = build_occurrences(
            task_type,
            due_date=cleaned_data.get("due_date"),
            schedule_date=cleaned_data.get("schedule_date"),
            start_time=cleaned_data.get("start_time"),
            end_time=cleaned_data.get("end_time"),
            repeat_days=cleaned_data.get("repeat_days"),
        )
        if (
            cleaned_data.get("status") in ACTIVE_TASK_STATUSES
            and schedule_has_conflict(
                cleaned_data.get("assigned_to"),
                occurrences,
                exclude_task_id=self.instance.pk,
            )
        ):
            raise forms.ValidationError(
                "La persona asignada ya tiene otra cita, llamada o tarea en ese tramo horario."
            )

        return cleaned_data

    def save(self, commit=True):
        task = super().save(commit=commit)
        if commit and task.task_type == "street_sweep":
            names = list(task.streets.values_list("name", flat=True))
            if len(names) <= 3:
                street_summary = ", ".join(names)
            else:
                street_summary = f"{', '.join(names[:3])} y {len(names) - 3} más"
            task.title = f"Peinar calles: {street_summary}"[:255]
            task.save(update_fields=["title"])
        return task
