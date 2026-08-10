from django import forms
from django.contrib.auth import get_user_model

from properties.models import Zone

from .models import Task


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
            "assigned_to",
            "priority",
            "due_date",
            "status",
        ]
        labels = {
            "task_type": "Tipo de tarea",
            "title": "Nombre de la tarea",
            "description": "Descripción",
            "zone": "Zona que se debe peinar",
            "assigned_to": "Persona asignada",
            "priority": "Prioridad",
            "due_date": "Fecha límite",
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
            "assigned_to": forms.Select(attrs={"class": INPUT_CLASS}),
            "priority": forms.Select(attrs={"class": INPUT_CLASS}),
            "due_date": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"class": INPUT_CLASS, "type": "datetime-local"},
            ),
            "status": forms.Select(attrs={"class": INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].required = False
        self.fields["description"].required = False
        self.fields["zone"].required = False
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
        self.fields["zone"].queryset = Zone.objects.all().order_by("name")
        self.fields["due_date"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean(self):
        cleaned_data = super().clean()
        task_type = cleaned_data.get("task_type")
        zone = cleaned_data.get("zone")

        if task_type == "custom":
            cleaned_data["zone"] = None
        elif task_type == "zone_sweep":
            if zone is not None:
                cleaned_data["title"] = f"Peinar zona {zone.name}"
            cleaned_data["description"] = ""

        return cleaned_data
