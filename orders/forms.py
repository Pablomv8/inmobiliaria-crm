from django import forms

from contacts.models import Contact
from properties.models import Property

from .models import Order, OrderComment
from users.permissions import assignable_agents, can_manage_assignments


INPUT_CLASS = (
    "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 "
    "text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-4 "
    "focus:ring-indigo-100 focus:outline-none"
)


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "buyer",
            "agent",
            "operation_type",
            "zone",
            "max_price",
            "payment_type",
            "property_type",
            "bedrooms",
            "bathrooms",
            "notes",
        ]
        widgets = {
            "buyer": forms.Select(attrs={"class": INPUT_CLASS}),
            "agent": forms.Select(attrs={"class": INPUT_CLASS}),
            "operation_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "zone": forms.Select(attrs={"class": INPUT_CLASS}),
            "max_price": forms.NumberInput(attrs={
                "class": f"{INPUT_CLASS} pr-12",
                "min": 0,
                "step": "0.01",
                "placeholder": "Ej: 250000",
            }),
            "payment_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "property_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "bedrooms": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": 0,
                "placeholder": "Opcional",
            }),
            "bathrooms": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": 0,
                "placeholder": "Opcional",
            }),
            "notes": forms.Textarea(attrs={
                "class": INPUT_CLASS,
                "rows": 4,
                "placeholder": "Preferencias o requisitos adicionales...",
            }),
        }

    def __init__(self, *args, buyer_obj=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        buyers = Contact.objects.filter(contact_type="buyer").order_by(
            "name", "last_name"
        )
        self.fields["buyer"].queryset = buyers
        self.fields["buyer"].empty_label = "Selecciona un comprador"
        self.fields["zone"].empty_label = "Cualquier zona"
        self.fields["operation_type"].choices = [
            ("", "Selecciona compra o alquiler"),
            *Order.OPERATION_TYPE_CHOICES,
        ]
        self.fields["operation_type"].error_messages["required"] = (
            "Este campo es obligatorio."
        )
        self.fields["payment_type"].choices = [
            ("", "Selecciona el tipo de pago"),
            *Order.PAYMENT_TYPE_CHOICES,
        ]
        self.fields["property_type"].choices = [
            ("", "Selecciona el tipo de inmueble"),
            *Property.PROPERTY_TYPE_CHOICES,
        ]

        if buyer_obj is not None:
            self.fields.pop("buyer")

        if can_manage_assignments(user):
            self.fields["agent"].queryset = assignable_agents(
                self.instance.agent if self.instance.pk else None
            )
            self.fields["agent"].empty_label = "Selecciona un responsable"
        else:
            self.fields.pop("agent")


class OrderCommentForm(forms.ModelForm):
    class Meta:
        model = OrderComment
        fields = ["text"]
        error_messages = {
            "text": {
                "required": "El comentario no puede estar vacío.",
            },
        }
        widgets = {
            "text": forms.Textarea(attrs={
                "class": INPUT_CLASS,
                "rows": 3,
                "maxlength": 500,
                "placeholder": "Añade una actualización del pedido...",
            }),
        }

    def clean_text(self):
        text = self.cleaned_data["text"].strip()
        if not text:
            raise forms.ValidationError("El comentario no puede estar vacío.")
        return text
