from django import forms

from contacts.models import Contact

from .models import Listing


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
            "start_date",
            "end_date",
            "commission_percent",
            "is_exclusive",
        ]
        labels = {
            "owner": "Propietario",
            "start_date": "Fecha de inicio",
            "end_date": "Fecha de conclusión",
            "commission_percent": "Comisión acordada (%)",
            "is_exclusive": "Encargo en exclusiva",
        }
        widgets = {
            "owner": forms.Select(attrs={"class": INPUT_CLASS}),
            "start_date": forms.DateInput(attrs={
                "class": INPUT_CLASS,
                "type": "date",
            }),
            "end_date": forms.DateInput(attrs={
                "class": INPUT_CLASS,
                "type": "date",
            }),
            "commission_percent": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": 0,
                "max": 100,
                "step": "0.01",
                "placeholder": "Ej: 3",
            }),
            "is_exclusive": forms.CheckboxInput(attrs={
                "class": "h-5 w-5 rounded border-gray-300 text-gray-900 focus:ring-gray-900",
            }),
        }

    def __init__(self, *args, property_obj, **kwargs):
        super().__init__(*args, **kwargs)

        owners = Contact.objects.filter(
            properties=property_obj,
            contact_type="owner",
        ).distinct()
        self.fields["owner"].queryset = owners
        self.fields["owner"].required = True
        self.fields["owner"].error_messages["invalid_choice"] = (
            "Selecciona un propietario asociado a este inmueble."
        )
        self.fields["end_date"].required = True
        self.fields["commission_percent"].required = True

        if not self.is_bound:
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
