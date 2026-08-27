from django import forms

from contacts.models import Contact

from .models import Listing, ListingComment
from users.permissions import assignable_agents, can_manage_assignments


INPUT_CLASS = (
    "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 "
    "text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-4 "
    "focus:ring-indigo-100 focus:outline-none"
)


class ListingForm(forms.ModelForm):

    class Meta:
        model = Listing
        fields = [
            "owner",
            "agent",
            "agreed_price",
            "start_date",
            "end_date",
            "commission_amount",
            "is_exclusive",
        ]
        labels = {
            "owner": "Propietario",
            "agreed_price": "Precio acordado del inmueble (€)",
            "start_date": "Fecha de inicio",
            "end_date": "Fecha de conclusión",
            "commission_amount": "Comisión acordada (€)",
            "is_exclusive": "Encargo en exclusiva",
        }
        widgets = {
            "owner": forms.Select(attrs={"class": INPUT_CLASS}),
            "agent": forms.Select(attrs={"class": INPUT_CLASS}),
            "agreed_price": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": "0.01",
                "step": "0.01",
                "placeholder": "Ej: 250000,00",
            }),
            "start_date": forms.DateInput(attrs={
                "class": INPUT_CLASS,
                "type": "date",
            }),
            "end_date": forms.DateInput(attrs={
                "class": INPUT_CLASS,
                "type": "date",
            }),
            "commission_amount": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": "0.01",
                "step": "0.01",
                "placeholder": "Ej: 7500,00",
            }),
            "is_exclusive": forms.CheckboxInput(attrs={
                "class": "h-5 w-5 rounded border-gray-300 text-gray-900 focus:ring-gray-900",
            }),
        }

    def __init__(self, *args, property_obj, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        owners = Contact.objects.filter(
            properties=property_obj,
            is_owner=True,
            is_archived=False,
        ).distinct()
        self.fields["owner"].queryset = owners
        self.fields["owner"].required = True
        self.fields["owner"].error_messages["invalid_choice"] = (
            "Selecciona un propietario asociado a este inmueble."
        )
        self.fields["end_date"].required = True
        self.fields["agreed_price"].required = True
        self.fields["agreed_price"].error_messages["required"] = (
            "Este campo es obligatorio."
        )
        self.fields["commission_amount"].required = True

        if can_manage_assignments(user):
            self.fields["agent"].queryset = assignable_agents(
                self.instance.agent if self.instance.pk else None
            )
            self.fields["agent"].empty_label = "Selecciona un responsable"
        else:
            self.fields.pop("agent")
            if self.instance.pk:
                for sensitive_field in (
                    "owner",
                    "agreed_price",
                    "commission_amount",
                    "is_exclusive",
                ):
                    self.fields.pop(sensitive_field)

        if not self.is_bound and "owner" in self.fields:
            self.fields["owner"].initial = owners.first()

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            self.add_error(
                "end_date",
                "La fecha de conclusión no puede ser anterior al inicio.",
            )

        return cleaned_data

    def clean_agreed_price(self):
        agreed_price = self.cleaned_data["agreed_price"]
        if agreed_price <= 0:
            raise forms.ValidationError(
                "El precio acordado debe ser mayor que cero."
            )
        return agreed_price

    def clean_commission_amount(self):
        commission = self.cleaned_data["commission_amount"]
        if commission <= 0:
            raise forms.ValidationError(
                "La comisión acordada debe ser mayor que cero."
            )
        return commission


class ListingCommentForm(forms.ModelForm):
    class Meta:
        model = ListingComment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": INPUT_CLASS,
                "rows": 3,
                "maxlength": 500,
                "placeholder": "Añade una actualización del encargo...",
            }),
        }
