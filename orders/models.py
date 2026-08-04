from django.db import models

from contacts.models import Contact
from properties.models import Property, Zone


class Order(models.Model):
    STATUS_CHOICES = [
        ("active", "Activo"),
        ("sale_appointment", "Cita de venta programada"),
        ("proposal_appointment", "Cita de propuesta programada"),
        ("proposal", "Propuesta realizada"),
        ("closed", "Cerrado"),
        ("cancelled", "Cancelado"),
    ]

    PAYMENT_TYPE_CHOICES = [
        ("cash", "Contado"),
        ("financing", "Financiación"),
    ]

    buyer = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name="orders",
        limit_choices_to={"contact_type": "buyer"},
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="active",
    )
    zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    max_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Presupuesto máximo",
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        verbose_name="Tipo de pago",
    )
    property_type = models.CharField(
        max_length=20,
        choices=Property.PROPERTY_TYPE_CHOICES,
        verbose_name="Tipo de inmueble",
    )
    bedrooms = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Habitaciones",
    )
    bathrooms = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Baños",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Otra información",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Pedido de {self.buyer} · {self.get_property_type_display()}"


class OrderComment(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_comments",
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comentario del pedido {self.order_id}"
