from django import forms
from .models import Appointment, Call

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
