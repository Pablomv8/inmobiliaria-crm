from django.db import models

from properties.models import Property
from contacts.models import Contact
from users.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone


class Sale(models.Model):

    STATUS_CHOICES = [
        ("draft", "Borrador"),
        ("signed", "Firmada"),
        ("cancelled", "Cancelada"),
    ]

    related_property = models.ForeignKey(
        Property,
        on_delete=models.PROTECT,
        related_name="sales"
    )

    buyer = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name="purchases"
    )

    agent = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="sales"
    )

    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    commission_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Comisión (€)",
    )

    seller_commission = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Comisión entregada por el vendedor (€)",
    )

    buyer_commission = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Comisión entregada por el comprador (€)",
    )

    deposit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Señal entregada (€)",
    )

    earnest_money_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Aportación de arras (€)",
    )

    sale_date = models.DateField(default=timezone.localdate)

    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="completed_sales",
        verbose_name="Encargo de origen",
    )

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="completed_sales",
        verbose_name="Pedido de origen",
    )

    proposal = models.ForeignKey(
        "calendar_app.ProposalAppointment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="completed_sales",
        verbose_name="Propuesta aceptada",
    )

    source_contract_appointment = models.OneToOneField(
        "calendar_app.Appointment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="completed_sale",
        verbose_name="Cita de contrato",
    )

    former_owner = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="former_property_sales",
        verbose_name="Propietario vendedor",
    )

    contract_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Referencia del contrato",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Venta de {self.related_property.full_address}"

    def save(self, *args, **kwargs):

        is_new = self.pk is None

        old_status = None

        if not is_new:
            old_status = Sale.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        # SOLO reaccionar si cambia estado o es nueva
        if is_new or old_status != self.status:

            if self.status == "signed":
                self.buyer.status = "closed"
                self.buyer.save()

            self.related_property.sync_status()

    def delete(self, *args, **kwargs):
        property_obj = self.related_property
        result = super().delete(*args, **kwargs)
        property_obj.sync_status()
        return result


class RentalContract(models.Model):
    STATUS_CHOICES = [
        ("signed", "Firmado"),
        ("cancelled", "Cancelado"),
    ]

    related_property = models.ForeignKey(
        Property,
        on_delete=models.PROTECT,
        related_name="rental_contracts",
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.PROTECT,
        related_name="rental_contracts",
        verbose_name="Encargo de origen",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rental_contracts",
        verbose_name="Pedido de origen",
    )
    proposal = models.ForeignKey(
        "calendar_app.ProposalAppointment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rental_contracts",
        verbose_name="Propuesta aceptada",
    )
    tenant = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name="rental_contracts_as_tenant",
        verbose_name="Inquilino",
    )
    owner = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name="rental_contracts_as_owner",
        verbose_name="Propietario",
    )
    agent = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="rental_contracts",
    )
    source_contract_appointment = models.OneToOneField(
        "calendar_app.Appointment",
        on_delete=models.PROTECT,
        related_name="completed_rental_contract",
        verbose_name="Cita de contrato",
    )
    rent_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Renta mensual acordada (€)",
    )
    deposit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Fianza o señal entregada (€)",
    )
    owner_commission = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Comisión entregada por el propietario (€)",
    )
    tenant_commission = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Comisión entregada por el inquilino (€)",
    )
    earnest_money_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Garantía o arras adicionales (€)",
    )
    contract_date = models.DateField(
        default=timezone.localdate,
        verbose_name="Fecha del contrato",
    )
    start_date = models.DateField(
        default=timezone.localdate,
        verbose_name="Inicio del alquiler",
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fin del alquiler",
    )
    contract_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Referencia del contrato",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="signed",
    )
    notes = models.TextField(blank=True, verbose_name="Observaciones")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-contract_date", "-created_at"]
        verbose_name = "Contrato de alquiler"
        verbose_name_plural = "Contratos de alquiler"

    @property
    def commission_amount(self):
        return self.owner_commission + self.tenant_commission

    def __str__(self):
        return f"Alquiler de {self.related_property.full_address}"
