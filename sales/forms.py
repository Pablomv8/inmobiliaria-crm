from django import forms
from .models import Sale
from properties.models import Property

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


class SaleForm(forms.ModelForm):
    

    class Meta:
        model = Sale

        fields = [
            "related_property",
            "buyer",
            "agent",
            "sale_price",
            "commission_amount",
            "sale_date",
            "notes",
        ]

        widgets = {
            "related_property": forms.Select(attrs={
                "class": INPUT_CLASS
            }),

            "buyer": forms.Select(attrs={
                "class": INPUT_CLASS
            }),

            "agent": forms.Select(attrs={
                "class": INPUT_CLASS
            }),

            "sale_price": forms.NumberInput(attrs={
                "class":INPUT_CLASS
            }),

            "commission_amount": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": 0,
                "step": "0.01",
                "placeholder": "Ej: 7500,00",
            }),

            "sale_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": INPUT_CLASS
                }
            ),

            "notes": forms.Textarea(attrs={
                "rows": 4,
                "class": INPUT_CLASS
            }),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["related_property"].queryset = (
            Property.objects.filter(
                status="active"
            )
    )
