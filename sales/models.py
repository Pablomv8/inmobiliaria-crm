from django.db import models

from properties.models import Property
from contacts.models import Contact
from users.models import User


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

    commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=3
    )

    sale_date = models.DateField()

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

    @property
    def commission_amount(self):

        return (
            self.sale_price *
            self.commission_percent / 100
        )
    
    def save(self, *args, **kwargs):

        is_new = self.pk is None

        old_status = None

        if not is_new:
            old_status = Sale.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        # SOLO reaccionar si cambia estado o es nueva
        if is_new or old_status != self.status:

            # VENTA COMPLETADA
            if self.status == "signed":

                self.related_property.status = "sold"
                self.related_property.save()

                # cerrar contacto
                self.buyer.status = "closed"
                self.buyer.save()

            # VENTA CANCELADA
            if self.status == "cancelled":

                self.related_property.status = "active"
                self.related_property.save()
