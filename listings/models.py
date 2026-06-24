from django.db import models
from django.utils import timezone

class Listing(models.Model):

    TYPE_CHOICES = [
        ("sale", "Venta"),
        ("rent", "Alquiler"),
    ]

    STATUS_CHOICES = [
        ("active", "Activo"),
        ("cancelled", "Cancelado"),
        ("sold", "Vendido"),
        ("rented", "Alquilado"),
    ]

    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="listings"
    )

    listing_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )

    owner_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    agency_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    owner_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    price_diference = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True
    )

    is_exclusive = models.BooleanField(
        default=False
    )

    start_date = models.DateField(
        default=timezone.now
    )

    end_date = models.DateField(
        null=True,
        blank=True
    )

    source_appointment = models.ForeignKey(
        "calendar_app.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_listing"
    )

    agent = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.property} - {self.get_listing_type_display()}"