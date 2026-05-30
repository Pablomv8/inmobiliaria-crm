from django import forms
from .models import Contact

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


class ContactForm(forms.ModelForm):

    class Meta:

        model = Contact

        fields = [
            'name',
            'phone',
            'email',
            'status',
            'notes',
            'properties',
            'assigned_agent'
        ]

        widgets = {

            'name': forms.TextInput(attrs={
                'class': INPUT_CLASS
            }),

            'phone': forms.TextInput(attrs={
                'class': INPUT_CLASS
            }),

            'email': forms.EmailInput(attrs={
                'class': INPUT_CLASS
            }),

            'status': forms.Select(attrs={
                'class': INPUT_CLASS
            }),

            'notes': forms.Textarea(attrs={
                'class': INPUT_CLASS,
                'rows': 5
            }),

            'properties': forms.SelectMultiple(attrs={
                'class': INPUT_CLASS
            }),

            'assigned_agent': forms.Select(attrs={
                'class': INPUT_CLASS
            }),
        }