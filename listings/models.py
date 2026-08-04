from django.db import models
from django.db import transaction
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator

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

    WORKFLOW_STATUS_CHOICES = [
        ("active", "Activo"),
        ("follow_up_appointment", "Seguimiento programado"),
        ("sale_appointment", "Visita programada"),
        ("proposal_appointment", "Cita de propuesta programada"),
        ("proposal", "Propuesta recibida"),
        ("closed", "Cerrado"),
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

    workflow_status = models.CharField(
        max_length=30,
        choices=WORKFLOW_STATUS_CHOICES,
        default="active",
        verbose_name="Estado del proceso",
    )

    owner_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    agency_price = models.DecimalField(
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

    commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
        verbose_name="Comisión acordada (%)",
    )

    owner = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="listings",
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

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if not is_new:
            return super().save(*args, **kwargs)

        with transaction.atomic():
            result = super().save(*args, **kwargs)
            changed = self.property.__class__.objects.filter(
                pk=self.property_id,
                status="prospect",
            ).update(status="active")
            if changed:
                self.property.status = "active"
            return result


class ListingComment(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listing_comments",
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comentario del encargo {self.listing_id}"
