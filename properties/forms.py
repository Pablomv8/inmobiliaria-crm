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
            'title',
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
            'price',
            'property_type',
            'image',
            'description',
            'status',
        ]

        widgets = {

            # BASIC INFO
            'title': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Ej: Piso luminoso en Salamanca'
            }),

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

            # PRICE
            'price': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': '250000'
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

        # 👇 forzamos tipo propietario
        self.fields["contact_type"].initial = "owner"
        self.fields["contact_type"].disabled = True

        # 👇 preseleccionamos inmueble
        if property_obj:
            self.fields["properties"].initial = [property_obj]
            self.fields["properties"].disabled = True

    class Meta:

        model = Contact

        fields = [
            "name",
            "phone",
            "email",
            "contact_type",
            "status",
            "notes",
            "properties",
            "assigned_agent",
        ]

        widgets = {

            "name": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Nombre del propietario",
            }),

            "phone": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "612 345 678",
            }),

            "email": forms.EmailInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "correo@email.com",
            }),

            "contact_type": forms.Select(attrs={
                "class": SELECT_CLASS,
            }),

            "status": forms.Select(attrs={
                "class": SELECT_CLASS,
            }),

            "notes": forms.Textarea(attrs={
                "class": TEXTAREA_CLASS,
                "rows": 4,
                "placeholder": "Notas del propietario...",
            }),

            "properties": forms.SelectMultiple(attrs={
                "class": "tom-select",
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