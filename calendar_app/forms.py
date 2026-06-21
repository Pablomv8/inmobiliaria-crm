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
            "appointment_type": forms.Select(attrs={
                "class": "w-full border rounded-lg p-2"
            }),
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full border rounded-lg p-2"
            }),
            "time": forms.TimeInput(attrs={
                "type": "time",
                "class": "w-full border rounded-lg p-2"
            }),
            "notes": forms.Textarea(attrs={
                "class": "w-full border rounded-lg p-2",
                "rows": 3
            })
        }

        
class CallForm(forms.ModelForm):

    class Meta:
        model = Call
        fields = [
            "date",
            "time",
            "notes"
        ]

        widgets = {
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full border rounded-lg p-2"
            }),
            "time": forms.TimeInput(attrs={
                "type": "time",
                "class": "w-full border rounded-lg p-2"
            }),
            "notes": forms.Textarea(attrs={
                "class": "w-full border rounded-lg p-2",
                "rows": 3
            })
        }