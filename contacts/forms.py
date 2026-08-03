from django import forms
from .models import Contact, Property
from django_select2.forms import Select2MultipleWidget

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
            "contact_type",
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

            "contact_type": "Tipo de contacto",

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

            "contact_type": forms.Select(attrs={
                "class": SELECT_CLASS,
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

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

        if phone:
            phone = phone.strip()

        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if email:
            email = email.lower().strip()

        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "")

        phone = "".join(filter(str.isdigit, phone))

        if phone:
            phone = f"+34{phone}"

        return phone