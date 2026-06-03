from django import forms
from .models import Sale
from properties.models import Property

class SaleForm(forms.ModelForm):

    class Meta:
        model = Sale

        fields = [
            "related_property",
            "buyer",
            "agent",
            "sale_price",
            "commission_percent",
            "sale_date",
            "notes",
        ]

        widgets = {
            "related_property": forms.Select(attrs={
                "class": "w-full rounded-xl border-gray-300"
            }),

            "buyer": forms.Select(attrs={
                "class": "w-full rounded-xl border-gray-300"
            }),

            "agent": forms.Select(attrs={
                "class": "w-full rounded-xl border-gray-300"
            }),

            "sale_price": forms.NumberInput(attrs={
                "class": "w-full rounded-xl border-gray-300"
            }),

            "commission_percent": forms.NumberInput(attrs={
                "class": "w-full rounded-xl border-gray-300"
            }),

            "sale_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-xl border-gray-300"
                }
            ),

            "notes": forms.Textarea(attrs={
                "rows": 4,
                "class": "w-full rounded-xl border-gray-300"
            }),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["related_property"].queryset = (
            Property.objects.filter(
                status="active"
            )
    )    