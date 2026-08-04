from django import forms
from listings.models import Listing

from .models import Appointment, Call, ProposalAppointment


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

    def __init__(self, *args, user=None, appointment_type=None, **kwargs):

        self.user = user

        super().__init__(*args, **kwargs)

        if appointment_type is not None:
            self.fields.pop("appointment_type")

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


class SaleAppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["listing", "date", "time", "notes"]
        widgets = {
            "listing": forms.Select(attrs={
                "class": "w-full border rounded-lg p-2",
            }),
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full border rounded-lg p-2",
            }),
            "time": forms.TimeInput(attrs={
                "type": "time",
                "id": "id_time",
                "class": "hidden",
            }),
            "notes": forms.Textarea(attrs={
                "class": "w-full border rounded-lg p-2",
                "rows": 3,
            }),
        }

    def __init__(self, *args, user, order, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        listings = Listing.objects.filter(
            status="active",
            listing_type="sale",
        ).select_related("property", "owner").order_by("property__street")

        self.fields["listing"].queryset = listings

    def clean(self):
        cleaned_data = super().clean()
        selected_date = cleaned_data.get("date")
        selected_time = cleaned_data.get("time")

        if not selected_date or not selected_time:
            return cleaned_data

        occupied = Appointment.objects.filter(
            agent=self.user,
            date=selected_date,
            time=selected_time,
            status="scheduled",
        ).exists()
        occupied = occupied or Call.objects.filter(
            agent=self.user,
            date=selected_date,
            time=selected_time,
            status="pending",
        ).exists()

        if occupied:
            raise forms.ValidationError(
                "Ya existe una cita o llamada en esa hora."
            )

        return cleaned_data


class ProposalAppointmentForm(forms.ModelForm):
    class Meta:
        model = ProposalAppointment
        fields = [
            "offered_price",
            "deposit_amount",
            "proposal_date",
            "end_date",
        ]
        widgets = {
            "offered_price": forms.NumberInput(attrs={
                "class": "w-full border rounded-xl p-3",
                "min": 0,
                "step": "0.01",
            }),
            "deposit_amount": forms.NumberInput(attrs={
                "class": "w-full border rounded-xl p-3",
                "min": 0,
                "step": "0.01",
            }),
            "proposal_date": forms.DateInput(attrs={
                "class": "w-full border rounded-xl p-3",
                "type": "date",
            }),
            "end_date": forms.DateInput(attrs={
                "class": "w-full border rounded-xl p-3",
                "type": "date",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        proposal_date = cleaned_data.get("proposal_date")
        end_date = cleaned_data.get("end_date")
        offered_price = cleaned_data.get("offered_price")
        deposit_amount = cleaned_data.get("deposit_amount")

        if proposal_date and end_date and end_date < proposal_date:
            self.add_error(
                "end_date",
                "La fecha final no puede ser anterior a la creación.",
            )
        if (
            offered_price is not None
            and deposit_amount is not None
            and deposit_amount > offered_price
        ):
            self.add_error(
                "deposit_amount",
                "La señal no puede superar el precio ofertado.",
            )
        if offered_price is not None and offered_price <= 0:
            self.add_error(
                "offered_price",
                "El precio ofertado debe ser mayor que cero.",
            )
        if deposit_amount is not None and deposit_amount < 0:
            self.add_error(
                "deposit_amount",
                "La señal no puede ser negativa.",
            )

        return cleaned_data
