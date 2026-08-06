from django import forms
from .models import Property


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

TEXTAREA_CLASS = INPUT_CLASS + " resize-y"

SELECT_CLASS = INPUT_CLASS


class PropertyForm(forms.ModelForm):

    class Meta:
        model = Property

        fields = [
            'street',
            'number',
            'postal_code',
            'city',
            'province',
            'zone',
            "bedrooms",
            "bathrooms",
            "area",
            "built_area",
            'property_type',
            'image',
            'description',
            'status',
        ]

        widgets = {

            # BASIC INFO
            'street': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Calle Alcalá'
            }),

            'number': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': '45'
            }),

            'postal_code': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': '28014'
            }),

            'city': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Madrid'
            }),

            'province': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Madrid'
            }),

            'zone': forms.Select(attrs={
                'class': SELECT_CLASS,
            }),

            # FEATURES
            'bedrooms': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'min': 0,
                'placeholder': '3'
            }),

            'bathrooms': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'min': 0,
                'placeholder': '2'
            }),

            'area': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'min': 0,
                'placeholder': '85'
            }),

            'built_area': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'min': 0,
                'placeholder': '95'
            }),

            # TYPE / STATUS
            'property_type': forms.Select(attrs={
                'class': SELECT_CLASS,
            }),

            'status': forms.Select(attrs={
                'class': SELECT_CLASS,
            }),

            # IMAGE
            'image': forms.ClearableFileInput(attrs={
                'class': 'w-full text-sm'
            }),

            # DESCRIPTION
            'description': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'rows': 5,
                'placeholder': 'Describe el inmueble...'
            }),
        }
from contacts.models import Contact

class OwnerContactForm(forms.ModelForm):

    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.property_obj = property_obj

        self.fields["marital_status"].choices = [
            ("", "Selecciona el estado civil"),
            *Contact.MARITAL_STATUS_CHOICES,
        ]
        self.fields["assigned_agent"].empty_label = "Sin agente asignado"

        for field in self.fields.values():
            field.error_messages["required"] = "Este campo es obligatorio."

        self.fields["email"].error_messages["invalid"] = (
            "Introduce un correo electrónico válido."
        )
        self.fields["birth_date"].error_messages["invalid"] = (
            "Introduce una fecha válida."
        )

    class Meta:

        model = Contact

        fields = [
            "name",
            "last_name",
            "identification_number",
            "marital_status",
            "birth_date",
            "occupation",

            "street",
            "number",
            "floor",
            "postal_code",
            "city",
            "province",

            "phone",
            "email",
            "notes",
            "assigned_agent",
        ]

        labels = {
            "name": "Nombre",
            "last_name": "Apellidos",
            "identification_number": "DNI, NIE o pasaporte",
            "marital_status": "Estado civil",
            "birth_date": "Fecha de nacimiento",
            "occupation": "Profesión",
            "street": "Calle",
            "number": "Número",
            "floor": "Piso o puerta",
            "postal_code": "Código postal",
            "city": "Localidad",
            "province": "Provincia",
            "phone": "Teléfono",
            "email": "Correo electrónico",
            "assigned_agent": "Agente asignado",
            "notes": "Notas internas",
        }

        help_texts = {
            "identification_number": "Documento identificativo del propietario.",
            "phone": "Número de contacto principal.",
            "assigned_agent": "Persona responsable de gestionar este propietario.",
            "notes": "Información interna visible para el equipo.",
        }

        widgets = {

            "name": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Nombre",
            }),

            "last_name": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Apellidos",
            }),

            "identification_number": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "12345678A",
            }),

            "marital_status": forms.Select(attrs={
                "class": SELECT_CLASS,
            }),

            "birth_date": forms.DateInput(attrs={
                "type": "date",
                "class": INPUT_CLASS,
            }),

            "occupation": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Profesión",
            }),

            "street": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Calle",
            }),

            "number": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Número",
            }),

            "floor": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Piso / Puerta",
            }),

            "postal_code": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "41001",
            }),

            "city": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Ciudad",
            }),

            "province": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Provincia",
            }),

            "phone": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "612 345 678",
                "autocomplete": "tel",
            }),

            "email": forms.EmailInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "correo@email.com",
            }),

            "notes": forms.Textarea(attrs={
                "class": TEXTAREA_CLASS,
                "rows": 4,
                "placeholder": "Notas del propietario...",
            }),

            "assigned_agent": forms.Select(attrs={
                "class": SELECT_CLASS,
            }),
        }

    def save(self, commit=True):

        contact = super().save(commit=False)

        contact.contact_type = "owner"

        if commit:
            contact.save()
            self.save_m2m()

            if self.property_obj:
                contact.properties.add(self.property_obj)

        return contact
