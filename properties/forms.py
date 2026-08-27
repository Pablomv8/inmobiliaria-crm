from django import forms
from contacts.models import Contact
from config.validators import (
    normalize_identity_document,
    normalize_phone_number,
    validate_identity_document,
    validate_phone_number,
    validate_spanish_postal_code,
)
from users.permissions import assignable_agents, can_manage_assignments

from .geocoding import is_arcos_de_la_frontera
from .models import Property, PropertyComment, Zone


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

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if can_manage_assignments(user):
            self.fields["assigned_agent"].queryset = assignable_agents(
                self.instance.assigned_agent if self.instance.pk else None
            )
            self.fields["assigned_agent"].required = True
            self.fields["assigned_agent"].empty_label = "Selecciona un responsable"
            if not self.is_bound and not self.instance.pk:
                self.fields["assigned_agent"].initial = user
        else:
            self.fields.pop("assigned_agent")
        self.fields["zone"].queryset = Zone.objects.order_by("name")
        self.fields["zone"].empty_label = "Selecciona una zona"
        self.fields["zone"].required = True
        self.fields["zone"].error_messages["required"] = (
            "Selecciona la zona comercial del inmueble."
        )
        selected_city = (
            self.data.get("city")
            if self.is_bound
            else self.initial.get("city", "Arcos de la Frontera")
        )
        self.fields["postal_code"].required = (
            not self.instance.pk and is_arcos_de_la_frontera(selected_city)
        )
        self.fields["postal_code"].error_messages["required"] = (
            "Introduce el código postal del inmueble."
        )
        selected_property_type = (
            self.data.get("property_type")
            if self.is_bound
            else (
                self.instance.property_type
                if self.instance.pk
                else self.initial.get("property_type")
            )
        )
        self.fields["floor"].required = selected_property_type == "flat"
        self.fields["door"].required = selected_property_type == "flat"
        self.fields["floor"].error_messages["required"] = (
            "Indica la planta del piso."
        )
        self.fields["door"].error_messages["required"] = (
            "Indica la puerta del piso."
        )
        self.fields["postal_code"].validators.append(
            validate_spanish_postal_code
        )
        self.fields["postal_code"].widget.attrs.update({
            "inputmode": "numeric",
            "pattern": r"(?:0[1-9]|[1-4][0-9]|5[0-2])[0-9]{3}",
            "maxlength": "5",
            "title": "Introduce un código postal español de 5 cifras.",
        })
        if not self.is_bound and not self.instance.pk:
            self.initial.setdefault("city", "Arcos de la Frontera")
            self.initial.setdefault("province", "Cádiz")

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")
        if (latitude is None) != (longitude is None):
            raise forms.ValidationError(
                "La ubicación del mapa debe incluir latitud y longitud."
            )
        if latitude is not None and not (-90 <= latitude <= 90):
            self.add_error("latitude", "La latitud seleccionada no es válida.")
        if longitude is not None and not (-180 <= longitude <= 180):
            self.add_error("longitude", "La longitud seleccionada no es válida.")
        return cleaned_data

    def clean_postal_code(self):
        return self.cleaned_data.get("postal_code", "").strip()

    class Meta:
        model = Property

        fields = [
            'street',
            'number',
            'block',
            'floor',
            'door',
            'postal_code',
            'city',
            'province',
            'latitude',
            'longitude',
            'zone',
            'assigned_agent',
            "bedrooms",
            "bathrooms",
            "area",
            "built_area",
            'property_type',
            'image',
            'description',
            'occupied_by',
        ]

        labels = {
            "street": "Calle",
            "number": "Número",
            "block": "Bloque o portal",
            "floor": "Planta",
            "door": "Puerta o local",
            "postal_code": "Código postal",
            "city": "Ciudad",
            "province": "Provincia",
            "latitude": "Latitud",
            "longitude": "Longitud",
            "zone": "Zona",
            "assigned_agent": "Agente responsable",
            "bedrooms": "Habitaciones",
            "bathrooms": "Baños",
            "area": "Superficie útil",
            "built_area": "Superficie construida",
            "property_type": "Tipo de inmueble",
            "image": "Imagen principal",
            "description": "Descripción",
            "occupied_by": "Ocupado por",
        }

        help_texts = {
            "zone": "Área comercial en la que se encuentra el inmueble.",
            "area": "Superficie útil expresada en metros cuadrados.",
            "built_area": "Superficie construida expresada en metros cuadrados.",
        }

        widgets = {

            # BASIC INFO
            'street': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Empieza a escribir, por ejemplo: Corredera',
                'autocomplete': 'off',
                'role': 'combobox',
                'aria-autocomplete': 'list',
                'aria-controls': 'address-suggestions',
                'aria-expanded': 'false',
            }),

            'number': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': '45'
            }),

            'block': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Ej. B o 2',
            }),

            'floor': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Ej. 2º',
            }),

            'door': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Ej. A',
            }),

            'postal_code': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': '28014'
            }),

            'city': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Arcos de la Frontera'
            }),

            'province': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Cádiz'
            }),

            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),

            'zone': forms.Select(attrs={
                'class': SELECT_CLASS,
            }),

            'assigned_agent': forms.Select(attrs={
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

            'occupied_by': forms.Select(attrs={
                'class': SELECT_CLASS,
            }),

            # IMAGE
            'image': forms.ClearableFileInput(attrs={
                'class': (
                    'block w-full rounded-xl border border-gray-300 bg-white '
                    'px-4 py-3 text-sm text-gray-700 shadow-sm '
                    'file:mr-4 file:rounded-lg file:border-0 file:bg-gray-100 '
                    'file:px-4 file:py-2 file:font-semibold file:text-gray-700 '
                    'hover:file:bg-gray-200'
                ),
                'accept': 'image/*',
            }),

            # DESCRIPTION
            'description': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'rows': 5,
                'placeholder': 'Describe el inmueble...'
            }),
        }

class OwnerContactForm(forms.ModelForm):

    def __init__(self, *args, property_obj=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.property_obj = property_obj
        self.user = user

        for field_name in (
            "last_name",
            "identification_number",
            "marital_status",
            "phone",
        ):
            self.fields[field_name].required = True

        self.fields["marital_status"].choices = [
            ("", "Selecciona el estado civil"),
            *Contact.MARITAL_STATUS_CHOICES,
        ]
        if can_manage_assignments(user):
            self.fields["assigned_agent"].queryset = assignable_agents()
            self.fields["assigned_agent"].required = True
            self.fields["assigned_agent"].empty_label = "Selecciona un agente"
            if not self.is_bound and not self.instance.pk and user is not None:
                self.fields["assigned_agent"].initial = user
        else:
            self.fields.pop("assigned_agent")

        for field in self.fields.values():
            field.error_messages["required"] = "Este campo es obligatorio."

        self.fields["email"].error_messages["invalid"] = (
            "Introduce un correo electrónico válido."
        )
        self.fields["birth_date"].error_messages["invalid"] = (
            "Introduce una fecha válida."
        )
        self.fields["phone"].validators.append(validate_phone_number)
        self.fields["postal_code"].validators.append(
            validate_spanish_postal_code
        )
        self.fields["identification_number"].validators.append(
            validate_identity_document
        )
        self.fields["phone"].widget.attrs.update({
            "inputmode": "tel",
            "pattern": r"(?:\+|00)?[0-9][0-9 ().-]{7,19}",
            "title": "Introduce un teléfono español o internacional válido.",
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

        contact.is_owner = True
        if "assigned_agent" not in self.fields:
            contact.assigned_agent = self.user

        if commit:
            contact.save()
            self.save_m2m()

            if self.property_obj:
                contact.properties.add(self.property_obj)

        return contact

    def clean_phone(self):
        return normalize_phone_number(self.cleaned_data.get("phone", ""))

    def clean_identification_number(self):
        return normalize_identity_document(
            self.cleaned_data.get("identification_number", "")
        )

    def clean_postal_code(self):
        return self.cleaned_data.get("postal_code", "").strip()

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").lower().strip()


class PropertyCommentForm(forms.ModelForm):
    class Meta:
        model = PropertyComment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": TEXTAREA_CLASS,
                "rows": 3,
                "maxlength": 1000,
                "placeholder": "Añade el resultado del contacto o una observación...",
            }),
        }

    def clean_text(self):
        text = self.cleaned_data["text"].strip()
        if not text:
            raise forms.ValidationError("El comentario no puede estar vacío.")
        return text
