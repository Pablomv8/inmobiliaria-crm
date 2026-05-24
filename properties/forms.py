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
            'address',
            'city',
            'price',
            'property_type',
            'image',
            'description',
        ]

        widgets = {

            'title': forms.TextInput(attrs={
                'class': INPUT_CLASS
            }),

            'address': forms.TextInput(attrs={
                'class': INPUT_CLASS
            }),

            'city': forms.TextInput(attrs={
                'class': INPUT_CLASS
            }),

            'price': forms.NumberInput(attrs={
                'class': INPUT_CLASS
            }),

            'property_type': forms.Select(attrs={
                'class': INPUT_CLASS
            }),

            'description': forms.Textarea(attrs={
                'class': INPUT_CLASS,
                'rows': 5
            }),
        }