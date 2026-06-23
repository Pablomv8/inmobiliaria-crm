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
    

    class Meta:

        model = Contact

        fields = [
            'name',
            'phone',
            'email',
            'contact_type',
            'status',
            'notes',
            'properties',
            'assigned_agent',
        ]

        labels = {
            'name': 'Nombre',
            'phone': 'Teléfono',
            'email': 'Correo electrónico',
            'contact_type': 'Tipo de contacto',
            'status': 'Estado',
            'notes': 'Notas',
            'properties': 'Inmuebles',
            'assigned_agent': 'Responsable',
        }

        help_texts = {
            'phone': 'Incluye prefijo internacional si aplica.',
            'properties': 'Puedes seleccionar varios inmuebles.',
            'notes': 'Información interna visible solo para el equipo.',
        }

        widgets = {

            'name': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Juan Pérez',
                'autocomplete': 'name',
            }),

            'phone': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': '+34 600 123 456',
                'autocomplete': 'tel',
            }),

            'email': forms.EmailInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'juan@email.com',
                'autocomplete': 'email',
            }),

            'contact_type': forms.Select(attrs={
                'class': SELECT_CLASS,
            }),

            'status': forms.Select(attrs={
                'class': SELECT_CLASS,
            }),

            'notes': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'rows': 5,
                'placeholder': 'Añade observaciones sobre el contacto...',
            }),

            'properties': Select2MultipleWidget(
                attrs={
                    'class': 'w-full'
                }
            ),

            'assigned_agent': forms.Select(attrs={
                'class': SELECT_CLASS,
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