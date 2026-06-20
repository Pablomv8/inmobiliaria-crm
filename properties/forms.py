from django import forms
from .models import Property


INPUT_CLASS = """
w-full
rounded-xl
border
border-gray-300
bg-gray-50
px-4
py-3
text-gray-800
placeholder-gray-400
focus:bg-white
focus:border-gray-900
focus:ring-2
focus:ring-gray-200
focus:outline-none
transition
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