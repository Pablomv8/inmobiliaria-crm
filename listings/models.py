from decimal import Decimal

from django.db import models
from django.db import transaction
from django.utils import timezone
from django.core.validators import MinValueValidator
from config.comment_audit import AuditedComment

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
        ("acceptance_appointment", "Aceptación programada"),
        ("counteroffer", "Contraoferta recibida"),
        ("contract_appointment", "Contrato programado"),
        ("signing_appointment", "Escrituración programada"),
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

    agreed_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Precio acordado (€)",
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

    commission_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="Comisión acordada (€)",
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

    class Meta:
        indexes = [
            models.Index(fields=["agent", "status", "end_date"], name="listing_agent_status_end"),
            models.Index(fields=["status", "workflow_status"], name="listing_status_workflow"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                name="listing_end_after_start",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(owner_price__gte=0)
                    & models.Q(agency_price__gte=0)
                    & models.Q(agreed_price__gt=0)
                    & (models.Q(commission_amount__isnull=True) | models.Q(commission_amount__gte=0))
                ),
                name="listing_valid_amounts",
            ),
        ]

    def __str__(self):
        return f"{self.property} - {self.get_listing_type_display()}"

    def save(self, *args, **kwargs):
        previous_property_id = None
        if self.pk:
            previous_property_id = Listing.objects.filter(pk=self.pk).values_list(
                "property_id",
                flat=True,
            ).first()

        with transaction.atomic():
            result = super().save(*args, **kwargs)
            property_ids = {
                property_id
                for property_id in [previous_property_id, self.property_id]
                if property_id
            }
            for property_obj in self.property.__class__.objects.filter(
                pk__in=property_ids,
            ):
                property_obj.sync_status()
            return result

    def delete(self, *args, **kwargs):
        property_obj = self.property
        with transaction.atomic():
            result = super().delete(*args, **kwargs)
            property_obj.sync_status()
            return result


class ListingComment(AuditedComment):
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
