from datetime import timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Goal


INPUT_CLASS = (
    "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 "
    "text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none "
    "focus:ring-4 focus:ring-indigo-100"
)


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = [
            "name",
            "description",
            "scope",
            "metric",
            "target_count",
            "start_date",
            "end_date",
            "assignees",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Ej. Captación comercial de septiembre",
            }),
            "description": forms.Textarea(attrs={
                "class": INPUT_CLASS,
                "rows": 3,
                "placeholder": "Añade contexto o indicaciones para el equipo.",
            }),
            "scope": forms.RadioSelect,
            "metric": forms.Select(attrs={"class": INPUT_CLASS}),
            "target_count": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": 1,
            }),
            "start_date": forms.DateInput(attrs={
                "class": INPUT_CLASS,
                "type": "date",
            }),
            "end_date": forms.DateInput(attrs={
                "class": INPUT_CLASS,
                "type": "date",
            }),
            "assignees": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["assignees"].queryset = User.objects.filter(
            is_active=True,
            role="agent",
        ).order_by("first_name", "last_name", "username")
        self.fields["assignees"].required = False
        if not self.is_bound and not self.instance.pk:
            today = timezone.localdate()
            self.initial.setdefault("start_date", today)
            self.initial.setdefault("end_date", today + timedelta(days=30))

    def clean(self):
        cleaned_data = super().clean()
        scope = cleaned_data.get("scope")
        assignees = cleaned_data.get("assignees")
        count = assignees.count() if assignees is not None else 0
        if scope == Goal.SCOPE_INDIVIDUAL and count != 1:
            self.add_error(
                "assignees",
                "Un objetivo individual debe tener exactamente un agente.",
            )
        elif scope == Goal.SCOPE_TEAM and count < 2:
            self.add_error(
                "assignees",
                "Un objetivo grupal debe incluir al menos dos agentes.",
            )
        return cleaned_data
