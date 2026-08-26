from django import forms
from .models import Contact, Property
from django_select2.forms import Select2MultipleWidget
from config.validators import (
    normalize_identity_document,
    normalize_phone_number,
    validate_identity_document,
    validate_phone_number,
    validate_spanish_postal_code,
)
from users.permissions import assignable_agents

INPUT_CLASS = """
w-full
rounded-xl
border
border-gray-300
bg-white
px-4
py-3
text-gray-900
shadow-sm
placeholder:text-gray-400
focus:border-indigo-500
focus:ring-4
focus:ring-indigo-100
focus:outline-none
transition-all
duration-200
"""

TEXTAREA_CLASS = """
w-full
rounded-xl
border
border-gray-300
bg-white
px-4
py-3
text-gray-900
shadow-sm
placeholder:text-gray-400
focus:border-indigo-500
focus:ring-4
focus:ring-indigo-100
focus:outline-none
transition-all
duration-200
resize-y
"""

SELECT_CLASS = """
w-full
rounded-xl
border
border-gray-300
bg-white
px-4
py-3
text-gray-900
shadow-sm
focus:border-indigo-500
focus:ring-4
focus:ring-indigo-100
focus:outline-none
transition-all
duration-200
"""


class ContactForm(forms.ModelForm):

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in (
            "last_name",
            "identification_number",
            "marital_status",
            "phone",
        ):
            self.fields[field_name].required = True
            self.fields[field_name].error_messages["required"] = (
                "Este campo es obligatorio."
            )

        current_agent = (
            self.instance.assigned_agent
            if self.instance and self.instance.pk
            else None
        )
        self.fields["assigned_agent"].queryset = assignable_agents(
            current_agent
        )
        self.fields["assigned_agent"].required = True
        self.fields["assigned_agent"].empty_label = "Selecciona un responsable"
        self.fields["assigned_agent"].error_messages["required"] = (
            "Selecciona la persona responsable del contacto."
        )
        if not self.is_bound and not self.instance.pk and user is not None:
            self.fields["assigned_agent"].initial = user
        self.fields["phone"].validators.append(validate_phone_number)
        self.fields["postal_code"].validators.append(
            validate_spanish_postal_code
        )
        self.fields["identification_number"].validators.append(
            validate_identity_document
        )
        self.fields["email"].error_messages["invalid"] = (
            "Introduce un correo electrónico válido."
        )
        self.fields["phone"].widget.attrs.update({
            "inputmode": "tel",
            "pattern": r"[6789](?:[ -]?\d){8}",
            "title": "Introduce 9 cifras; debe comenzar por 6, 7, 8 o 9.",
        })
        self.fields["postal_code"].widget.attrs.update({
            "inputmode": "numeric",
            "pattern": r"(?:0[1-9]|[1-4][0-9]|5[0-2])[0-9]{3}",
            "maxlength": "5",
            "title": "Introduce un código postal español de 5 cifras.",
        })
        self.fields["identification_number"].widget.attrs.update({
            "pattern": r"[A-Za-z0-9][A-Za-z0-9 -]{5,29}",
            "title": "Introduce un DNI, NIE o pasaporte válido.",
        })

        if self.instance and self.instance.pk and self.instance.phone:

            phone = self.instance.phone.strip()

            if phone.startswith("+34"):
                phone = phone[3:]

            self.initial["phone"] = phone

    class Meta:

        model = Contact

        fields = [
            "name",
            "last_name",
            "street",
            "number",
            "floor",
            "postal_code",
            "city",
            "province",
            "identification_number",
            "marital_status",
            "birth_date",
            "occupation",
            "phone",
            "email",
            "is_owner",
            "is_buyer",
            "notes",
            "properties",
            "assigned_agent",
        ]

        labels = {
            "name": "Nombre",
            "last_name": "Apellidos",

            "identification_number": "Documento de identidad",
            "marital_status": "Estado civil",
            "birth_date": "Fecha de nacimiento",
            "occupation": "Profesión",

            "street": "Calle",
            "number": "Número",
            "floor": "Piso / Puerta",
            "postal_code": "Código postal",
            "city": "Ciudad",
            "province": "Provincia",

            "phone": "Teléfono",
            "email": "Correo electrónico",

            "is_owner": "Propietario",
            "is_buyer": "Comprador",

            "notes": "Notas",

            "properties": "Inmuebles",

            "assigned_agent": "Responsable",
        }

        help_texts = {
            "phone": "Incluye prefijo internacional si aplica.",
            "properties": "Puedes seleccionar varios inmuebles.",
            "notes": "Información interna visible solo para el equipo.",
        }

        widgets = {

            "name": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Juan",
                "autocomplete": "given-name",
            }),

            "last_name": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Pérez García",
                "autocomplete": "family-name",
            }),

            "address": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "C/ Ejemplo 12, Sevilla",
                "autocomplete": "street-address",
            }),

            "identification_number": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "12345678A",
                "autocomplete": "off",
            }),

            "marital_status": forms.Select(attrs={
                "class": SELECT_CLASS,
            }),

            "phone": forms.TextInput(attrs={
                "id": "id_phone",
                "placeholder": "612 345 678",
                "autocomplete": "tel",
                "maxlength": "11",
                "class": """
                    w-full
                    rounded-r-xl
                    border
                    border-gray-300
                    px-4
                    py-3
                    focus:border-indigo-500
                    focus:ring-4
                    focus:ring-indigo-100
                    focus:outline-none
                """
            }),

            "email": forms.EmailInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "juan@email.com",
                "autocomplete": "email",
            }),

            "is_owner": forms.CheckboxInput(attrs={
                "class": "h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500",
            }),

            "is_buyer": forms.CheckboxInput(attrs={
                "class": "h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500",
            }),

            "notes": forms.Textarea(attrs={
                "class": TEXTAREA_CLASS,
                "rows": 5,
                "placeholder": "Añade observaciones sobre el contacto...",
            }),

            "properties": forms.SelectMultiple(attrs={
                "class": "tom-select",
            }),

            "assigned_agent": forms.Select(attrs={
                "class": SELECT_CLASS,
            }),

            "street": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Calle Real",
                "autocomplete": "address-line1",
            }),

            "number": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "25",
                "autocomplete": "address-line2",
            }),

            "floor": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "3º B",
            }),

            "postal_code": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "41001",
                "autocomplete": "postal-code",
            }),

            "city": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Sevilla",
                "autocomplete": "address-level2",
            }),

            "province": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Sevilla",
                "autocomplete": "address-level1",
            }),

            "birth_date": forms.DateInput(attrs={
                "type": "date",
                "class": INPUT_CLASS,
            }),

            "occupation": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Arquitecto",
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if email:
            email = email.lower().strip()

        return email
    
    def clean_phone(self):
        return normalize_phone_number(self.cleaned_data.get("phone", ""))

    def clean_identification_number(self):
        return normalize_identity_document(
            self.cleaned_data.get("identification_number", "")
        )

    def clean_postal_code(self):
        return self.cleaned_data.get("postal_code", "").strip()

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("is_owner") and not cleaned_data.get("is_buyer"):
            raise forms.ValidationError(
                "Selecciona al menos un rol: propietario o comprador."
            )

        if not cleaned_data.get("is_owner"):
            # Un comprador no puede recibir inmuebles desde este formulario.
            # En edición conservamos relaciones históricas ya existentes.
            if self.instance and self.instance.pk:
                cleaned_data["properties"] = self.instance.properties.all()
            else:
                cleaned_data["properties"] = Property.objects.none()

        return cleaned_data
