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
                'id': 'id_phone',
                'placeholder': '612 345 678',
                'autocomplete': 'tel',
                'maxlength': '11',
                'class': """
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

            'properties': forms.SelectMultiple(attrs={
                'class': 'tom-select',
            }),

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
    
    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "")

        phone = "".join(filter(str.isdigit, phone))

        if phone:
            phone = f"+34{phone}"

        return phone