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

            # TITLE
            'title': forms.TextInput(attrs={
                'class': INPUT_CLASS
            }),

            # STREET
            'street': forms.TextInput(attrs={
                'class': INPUT_CLASS
            }),

            # NUMBER
            'number': forms.TextInput(attrs={
                'class': INPUT_CLASS
            }),

            # POSTAL CODE
            'postal_code': forms.TextInput(attrs={
                'class': INPUT_CLASS
            }),

            # CITY
            'city': forms.TextInput(attrs={
                'class': INPUT_CLASS
            }),

            # PROVINCE
            'province': forms.TextInput(attrs={
                'class': INPUT_CLASS
            }),

            "zone": forms.Select(attrs={
                "class": INPUT_CLASS,
            }),

            "bedrooms": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": 0,
            }),

            "bathrooms": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": 0,
            }),

            "area": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": 0,
            }),

            "built_area": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": 0,
            }),

            # PRICE
            'price': forms.NumberInput(attrs={
                'class': INPUT_CLASS
            }),

            # TYPE
            'property_type': forms.Select(attrs={
                'class': INPUT_CLASS
            }),

            # STATUS (IMPORTANTE PARA CRM)
            'status': forms.Select(attrs={
                'class': INPUT_CLASS
            }),

            # IMAGE
            'image': forms.ClearableFileInput(attrs={
                'class': INPUT_CLASS
            }),

            # DESCRIPTION
            'description': forms.Textarea(attrs={
                'class': INPUT_CLASS,
                'rows': 5
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