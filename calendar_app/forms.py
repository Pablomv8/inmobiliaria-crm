from datetime import date, timedelta
from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from listings.models import Listing

from .scheduling import schedule_has_conflict, slot_has_conflict

from .models import (
    Appointment,
    Call,
    CallComment,
    CounterOffer,
    ProposalAppointment,
    ProposalComment,
)


class CallCommentForm(forms.ModelForm):
    class Meta:
        model = CallComment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": "w-full border border-gray-300 rounded-xl p-3 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 focus:outline-none",
                "rows": 3,
                "maxlength": 1000,
                "placeholder": "Añade el resultado o una observación de la llamada...",
            }),
        }
        error_messages = {
            "text": {"required": "El comentario no puede estar vacío."},
        }

    def clean_text(self):
        text = self.cleaned_data["text"].strip()
        if not text:
            raise forms.ValidationError("El comentario no puede estar vacío.")
        return text


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


class FollowUpDecisionForm(forms.Form):
    action = forms.ChoiceField(
        choices=Appointment.FOLLOW_UP_ACTION_CHOICES,
        widget=forms.HiddenInput(),
        error_messages={
            "required": "Selecciona una acción para el encargo.",
            "invalid_choice": "La acción seleccionada no es válida.",
        },
    )
    new_price = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        label="Nuevo precio acordado (€)",
        widget=forms.NumberInput(attrs={
            "class": "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-gray-900 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 focus:outline-none",
            "min": "0.01",
            "step": "0.01",
        }),
    )
    new_end_date = forms.DateField(
        required=False,
        label="Nueva fecha de conclusión",
        widget=forms.DateInput(attrs={
            "class": "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-gray-900 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 focus:outline-none",
            "type": "date",
        }),
    )

    def __init__(self, *args, listing, **kwargs):
        super().__init__(*args, **kwargs)
        self.listing = listing
        self.fields["new_price"].widget.attrs["placeholder"] = (
            f"Menos de {listing.agreed_price} €"
        )
        price_ceiling = listing.agreed_price - Decimal("0.01")
        if price_ceiling > 0:
            self.fields["new_price"].widget.attrs["max"] = price_ceiling

        renewal_baseline = listing.end_date or max(listing.start_date, date.today())
        self.fields["new_end_date"].widget.attrs["min"] = (
            renewal_baseline + timedelta(days=1)
        ).isoformat()

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")

        if action == "price_reduction":
            new_price = cleaned_data.get("new_price")
            if new_price is None:
                self.add_error(
                    "new_price",
                    "Indica el nuevo precio acordado.",
                )
            elif new_price >= self.listing.agreed_price:
                self.add_error(
                    "new_price",
                    "El nuevo precio debe ser inferior al precio acordado actual.",
                )

        if action == "renewal":
            new_end_date = cleaned_data.get("new_end_date")
            renewal_baseline = self.listing.end_date or max(
                self.listing.start_date,
                date.today(),
            )
            if new_end_date is None:
                self.add_error(
                    "new_end_date",
                    "Indica la nueva fecha de conclusión.",
                )
            elif new_end_date <= renewal_baseline:
                self.add_error(
                    "new_end_date",
                    "La nueva fecha debe ampliar la vigencia actual del encargo.",
                )

        return cleaned_data


class AppointmentEditForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["agent", "date", "time", "end_time", "notes"]
        labels = {
            "agent": "Agente asignado",
            "date": "Fecha",
            "time": "Hora",
            "end_time": "Hora de fin",
            "notes": "Notas",
        }
        widgets = {
            "agent": forms.Select(attrs={
                "class": "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-4 focus:ring-indigo-100",
            }),
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-4 focus:ring-indigo-100",
            }),
            "time": forms.TimeInput(attrs={
                "type": "time",
                "step": "1800",
                "class": "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-4 focus:ring-indigo-100",
            }),
            "end_time": forms.TimeInput(attrs={
                "type": "time",
                "step": "1800",
                "class": "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-4 focus:ring-indigo-100",
            }),
            "notes": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Indicaciones o información relevante para la cita...",
                "class": "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-4 focus:ring-indigo-100",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["agent"].queryset = (
            get_user_model().objects.filter(is_active=True).order_by(
                "first_name",
                "last_name",
                "username",
            )
        )
        self.fields["agent"].empty_label = None

    def clean(self):
        cleaned_data = super().clean()
        agent = cleaned_data.get("agent")
        selected_date = cleaned_data.get("date")
        selected_time = cleaned_data.get("time")
        end_time = cleaned_data.get("end_time")

        if selected_time and end_time and end_time <= selected_time:
            self.add_error(
                "end_time",
                "La hora de fin debe ser posterior a la hora de inicio.",
            )
            return cleaned_data

        if (
            self.instance.status != "scheduled"
            or agent is None
            or selected_date is None
            or selected_time is None
            or end_time is None
        ):
            return cleaned_data

        occupied = schedule_has_conflict(
            agent,
            selected_date,
            selected_time,
            end_time,
            exclude_appointment_id=self.instance.pk,
        )

        if occupied:
            raise forms.ValidationError(
                "El agente seleccionado ya tiene otra cita, llamada o tarea en ese intervalo."
            )

        return cleaned_data

class AppointmentForm(forms.ModelForm):

    class Meta:

        model = Appointment

        fields = [
            "appointment_type",
            "date",
            "time",
            "end_time",
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
                    "step": "1800",
                    "class": "w-full border rounded-lg p-2"
                }
            ),

            "end_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "id": "id_end_time",
                    "step": "1800",
                    "class": "w-full border rounded-lg p-2"
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
        start_time = cleaned_data.get("time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time and end_time <= start_time:
            self.add_error(
                "end_time",
                "La hora de fin debe ser posterior a la hora de inicio.",
            )
            return cleaned_data

        if not date or not start_time or not end_time:
            return cleaned_data

        occupied = schedule_has_conflict(
            self.user,
            date,
            start_time,
            end_time,
            exclude_appointment_id=self.instance.pk,
        )

        if occupied:

            raise forms.ValidationError(
                "Ya existe una cita, llamada o tarea que se solapa con ese intervalo."
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

        occupied = slot_has_conflict(
            self.user,
            date,
            time,
        )

        if occupied:

            raise forms.ValidationError(
                "Ya existe una cita, llamada o tarea en esa hora."
            )

        return cleaned_data


class SaleAppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["listing", "date", "time", "end_time", "notes"]
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
                "step": "1800",
                "class": "w-full border rounded-lg p-2",
            }),
            "end_time": forms.TimeInput(attrs={
                "type": "time",
                "id": "id_end_time",
                "step": "1800",
                "class": "w-full border rounded-lg p-2",
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
        end_time = cleaned_data.get("end_time")

        if selected_time and end_time and end_time <= selected_time:
            self.add_error(
                "end_time",
                "La hora de fin debe ser posterior a la hora de inicio.",
            )
            return cleaned_data

        if not selected_date or not selected_time or not end_time:
            return cleaned_data

        occupied = schedule_has_conflict(
            self.user,
            selected_date,
            selected_time,
            end_time,
            exclude_appointment_id=self.instance.pk,
        )

        if occupied:
            raise forms.ValidationError(
                "Ya existe una cita, llamada o tarea que se solapa con ese intervalo."
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


class ProposalCommentForm(forms.ModelForm):
    class Meta:
        model = ProposalComment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-gray-900 shadow-sm focus:border-green-500 focus:ring-4 focus:ring-green-100 focus:outline-none",
                "rows": 3,
                "maxlength": 1000,
                "placeholder": "Añade una observación, acuerdo o actualización de la propuesta...",
            }),
        }
        error_messages = {
            "text": {"required": "El comentario no puede estar vacío."},
        }

    def clean_text(self):
        text = self.cleaned_data["text"].strip()
        if not text:
            raise forms.ValidationError("El comentario no puede estar vacío.")
        return text


class CounterOfferForm(forms.ModelForm):
    class Meta:
        model = CounterOffer
        fields = ["counteroffer_date", "owner_price", "notes"]
        widgets = {
            "counteroffer_date": forms.DateInput(attrs={
                "class": "w-full border rounded-xl p-3",
                "type": "date",
            }),
            "owner_price": forms.NumberInput(attrs={
                "class": "w-full border rounded-xl p-3",
                "min": 0,
                "step": "0.01",
            }),
            "notes": forms.Textarea(attrs={
                "class": "w-full border rounded-xl p-3",
                "rows": 4,
                "placeholder": "Condiciones o información adicional...",
            }),
        }

    def clean_owner_price(self):
        price = self.cleaned_data["owner_price"]
        if price <= 0:
            raise forms.ValidationError(
                "El precio solicitado debe ser mayor que cero."
            )
        return price
