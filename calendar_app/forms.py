from django import forms
from .models import Appointment, Call


class AppointmentResultForm(forms.ModelForm):

    class Meta:
        model = Appointment
        fields = ["result_comment"]
        widgets = {
            "result_comment": forms.Textarea(attrs={
                "class": "w-full border border-gray-300 rounded-xl p-3 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 focus:outline-none",
                "rows": 4,
                "maxlength": 1000,
                "placeholder": "Resume el resultado de la cita...",
            }),
        }

    def clean_result_comment(self):
        comment = self.cleaned_data["result_comment"].strip()

        if not comment:
            raise forms.ValidationError(
                "Añade un comentario antes de completar la cita."
            )

        return comment

class AppointmentForm(forms.ModelForm):

    class Meta:

        model = Appointment

        fields = [
            "appointment_type",
            "date",
            "time",
            "notes"
        ]

        widgets = {

            "appointment_type": forms.Select(
                attrs={
                    "class": "w-full border rounded-lg p-2"
                }
            ),

            "date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full border rounded-lg p-2"
                }
            ),

            "time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "id": "id_time",
                    "class": "hidden"
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "w-full border rounded-lg p-2",
                    "rows": 3
                }
            )
        }

    def __init__(self, *args, user=None, **kwargs):

        self.user = user

        super().__init__(*args, **kwargs)

    def clean(self):

        cleaned_data = super().clean()

        date = cleaned_data.get("date")
        time = cleaned_data.get("time")

        if not date or not time:
            return cleaned_data

        occupied = (
            Appointment.objects.filter(
                agent=self.user,
                date=date,
                time=time,
                status="scheduled"
            )
            .exclude(pk=self.instance.pk)
            .exists()
        )

        occupied = occupied or (
            Call.objects.filter(
                agent=self.user,
                date=date,
                time=time,
                status="pending"
            )
            .exists()
        )

        if occupied:

            raise forms.ValidationError(
                "Ya existe una cita o llamada en esa hora."
            )

        return cleaned_data

class CallForm(forms.ModelForm):

    class Meta:

        model = Call

        fields = [
            "date",
            "time",
            "notes"
        ]

        widgets = {

            "date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full border rounded-lg p-2"
                }
            ),

            "time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "id": "id_time",
                    "class": "hidden"
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "w-full border rounded-lg p-2",
                    "rows": 3
                }
            )
        }
    
    def __init__(self, *args, user=None, **kwargs):

        self.user = user

        super().__init__(*args, **kwargs)

    def clean(self):

        cleaned_data = super().clean()

        date = cleaned_data.get("date")
        time = cleaned_data.get("time")

        if not date or not time:
            return cleaned_data

        occupied = (
            Appointment.objects.filter(
                agent=self.user,
                date=date,
                time=time,
                status="scheduled"
            )
            .exclude(pk=self.instance.pk)
            .exists()
        )

        occupied = occupied or (
            Call.objects.filter(
                agent=self.user,
                date=date,
                time=time,
                status="pending"
            )
            .exists()
        )

        if occupied:

            raise forms.ValidationError(
                "Ya existe una cita o llamada en esa hora."
            )

        return cleaned_data
