from django import forms
from decimal import Decimal

from django.core.exceptions import ValidationError

from .models import RentalContract, Sale
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
            "deposit_amount",
            "earnest_money_amount",
            "seller_commission",
            "buyer_commission",
            "sale_date",
            "contract_reference",
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

            "seller_commission": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": 0,
                "step": "0.01",
                "placeholder": "Ej: 7500,00",
            }),

            "buyer_commission": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": 0,
                "step": "0.01",
            }),

            "deposit_amount": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": 0,
                "step": "0.01",
            }),

            "earnest_money_amount": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": 0,
                "step": "0.01",
            }),

            "sale_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": INPUT_CLASS
                }
            ),

            "contract_reference": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Opcional",
            }),

            "notes": forms.Textarea(attrs={
                "rows": 4,
                "class": INPUT_CLASS
            }),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["related_property"].queryset = (
            Property.objects.exclude(status__in=["sold", "rented"])
        )

    def save(self, commit=True):
        sale = super().save(commit=False)
        sale.commission_amount = (
            sale.seller_commission + sale.buyer_commission
        )
        if commit:
            sale.save()
        return sale


class SaleClosingForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = [
            "sale_price",
            "deposit_amount",
            "earnest_money_amount",
            "seller_commission",
            "buyer_commission",
            "contract_reference",
            "notes",
        ]
        widgets = {
            field: forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": "0",
                "step": "0.01",
            })
            for field in [
                "sale_price",
                "deposit_amount",
                "earnest_money_amount",
                "seller_commission",
                "buyer_commission",
            ]
        } | {
            "contract_reference": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Opcional: número o referencia interna",
            }),
            "notes": forms.Textarea(attrs={
                "class": INPUT_CLASS,
                "rows": 4,
                "placeholder": "Condiciones finales u observaciones...",
            }),
        }

    def __init__(self, *args, appointment, **kwargs):
        super().__init__(*args, **kwargs)
        self.appointment = appointment
        proposal = appointment.purchase_proposal
        listing = appointment.listing or (proposal.listing if proposal else None)
        if not self.is_bound:
            self.initial.update({
                "sale_price": (
                    proposal.offered_price
                    if proposal
                    else listing.agreed_price
                ),
                "deposit_amount": proposal.deposit_amount if proposal else 0,
                "seller_commission": (
                    listing.commission_amount
                    if listing and listing.commission_amount is not None
                    else 0
                ),
                "buyer_commission": 0,
                "earnest_money_amount": 0,
            })

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get("sale_price")
        deposit = cleaned_data.get("deposit_amount") or Decimal("0")
        earnest = cleaned_data.get("earnest_money_amount") or Decimal("0")
        if price is not None and price <= 0:
            self.add_error("sale_price", "El precio de compra debe ser mayor que cero.")
        if price is not None and deposit + earnest > price:
            raise ValidationError(
                "La suma de la señal y las arras no puede superar el precio de compra."
            )
        return cleaned_data


class SaleCorrectionForm(forms.Form):
    sale_price = forms.DecimalField(label="Precio de compra (€)", min_value=0.01, widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.01"}))
    deposit_amount = forms.DecimalField(label="Señal (€)", min_value=0, widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.01"}))
    earnest_money_amount = forms.DecimalField(label="Arras (€)", min_value=0, widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.01"}))
    seller_commission = forms.DecimalField(label="Comisión del vendedor (€)", min_value=0, widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.01"}))
    buyer_commission = forms.DecimalField(label="Comisión del comprador (€)", min_value=0, widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.01"}))
    sale_date = forms.DateField(label="Fecha", widget=forms.DateInput(attrs={"class": INPUT_CLASS, "type": "date"}))
    contract_reference = forms.CharField(label="Referencia", required=False, widget=forms.TextInput(attrs={"class": INPUT_CLASS}))
    notes = forms.CharField(label="Notas", required=False, widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}))
    reason = forms.CharField(label="Motivo de la corrección", widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3, "placeholder": "Explica por qué se corrige el registro firmado..."}))

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get("sale_price")
        deposit = cleaned_data.get("deposit_amount") or Decimal("0")
        earnest = cleaned_data.get("earnest_money_amount") or Decimal("0")
        if price is not None and deposit + earnest > price:
            raise ValidationError("La suma de señal y arras no puede superar el precio.")
        return cleaned_data


class RentalContractClosingForm(forms.ModelForm):
    class Meta:
        model = RentalContract
        fields = [
            "rent_price",
            "deposit_amount",
            "earnest_money_amount",
            "owner_commission",
            "tenant_commission",
            "start_date",
            "end_date",
            "contract_reference",
            "notes",
        ]
        widgets = {
            field: forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": "0",
                "step": "0.01",
            })
            for field in [
                "rent_price",
                "deposit_amount",
                "earnest_money_amount",
                "owner_commission",
                "tenant_commission",
            ]
        } | {
            "start_date": forms.DateInput(attrs={
                "class": INPUT_CLASS,
                "type": "date",
            }),
            "end_date": forms.DateInput(attrs={
                "class": INPUT_CLASS,
                "type": "date",
            }),
            "contract_reference": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Opcional: número o referencia interna",
            }),
            "notes": forms.Textarea(attrs={
                "class": INPUT_CLASS,
                "rows": 4,
                "placeholder": "Duración, condiciones u observaciones...",
            }),
        }

    def __init__(self, *args, appointment, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["end_date"].required = True
        self.fields["end_date"].error_messages["required"] = (
            "Indica la fecha de finalización del alquiler."
        )
        proposal = appointment.purchase_proposal
        listing = appointment.listing or (proposal.listing if proposal else None)
        if not self.is_bound:
            self.initial.update({
                "rent_price": (
                    proposal.offered_price
                    if proposal
                    else listing.agreed_price
                ),
                "deposit_amount": proposal.deposit_amount if proposal else 0,
                "owner_commission": (
                    listing.commission_amount
                    if listing and listing.commission_amount is not None
                    else 0
                ),
                "tenant_commission": 0,
                "earnest_money_amount": 0,
            })

    def clean(self):
        cleaned_data = super().clean()
        rent_price = cleaned_data.get("rent_price")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if rent_price is not None and rent_price <= 0:
            self.add_error("rent_price", "La renta mensual debe ser mayor que cero.")
        if start_date and end_date and end_date <= start_date:
            self.add_error(
                "end_date",
                "La fecha de fin debe ser posterior al inicio del alquiler.",
            )
        return cleaned_data
