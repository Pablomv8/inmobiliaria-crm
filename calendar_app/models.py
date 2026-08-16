from django.db import models
from django.core.exceptions import ValidationError

# Create your models here.
from django.db import models

from users.models import User

from contacts.models import Contact
from properties.models import Property
from news.models import News



class Appointment(models.Model):

    TYPE_CHOICES = [
        ("acquisition", "Adquisición"),
        ("sale", "Venta"),
        ("valuation", "Valoración"),
        ("signing", "Escrituración"),
        ("follow_up", "Seguimiento"),
        ("proposal", "Propuesta"),
        ("proposal_acceptance", "Aceptación de propuesta"),
        ("contract", "Contrato"),
    ]

    STATUS_CHOICES = [
        ("scheduled", "Programada"),
        ("completed", "Completada"),
        ("cancelled", "Cancelada"),
    ]

    related_property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE
    )

    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE
    )

    agent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    appointment_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES
    )

    date = models.DateField()

    time = models.TimeField()

    end_time = models.TimeField(
        verbose_name="Hora de fin",
    )

    notes = models.TextField(
        blank=True
    )

    result_comment = models.TextField(
        blank=True,
        verbose_name="Comentario de resultado",
    )

    result_success = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Cita con éxito",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="scheduled"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    news = models.ForeignKey(
        News,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments"
    )

    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="follow_up_appointments",
    )

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sale_appointments",
    )

    source_sale_appointment = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposal_appointment",
        verbose_name="Cita de venta origen",
    )

    purchase_proposal = models.ForeignKey(
        "calendar_app.ProposalAppointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
        verbose_name="Propuesta de compra",
    )

    source_acceptance_appointment = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resulting_appointments",
        verbose_name="Cita de aceptación origen",
    )

    source_counteroffer = models.ForeignKey(
        "calendar_app.CounterOffer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="response_appointments",
        verbose_name="Contraoferta a la que responde",
    )

    def clean(self):
        super().clean()
        if self.time and self.end_time and self.end_time <= self.time:
            raise ValidationError({
                "end_time": "La hora de fin debe ser posterior a la hora de inicio.",
            })

    def __str__(self):
        return (
            f"{self.get_appointment_type_display()} "
            f"{self.date}"
        )


class Call(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("completed", "Completada"),
        ("cancelled", "Cancelada"),
    ]

    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE
    )

    agent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    date = models.DateField()

    time = models.TimeField()

    notes = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    news = models.ForeignKey(
        News,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calls"
    )

    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calls",
    )

    def __str__(self):
        return (
            f"Llamada {self.date} a las {self.time}"
        )


class CallComment(models.Model):
    call = models.ForeignKey(
        Call,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="call_comments",
    )
    text = models.TextField(verbose_name="Comentario")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Comentario de llamada"
        verbose_name_plural = "Comentarios de llamada"

    def __str__(self):
        return f"Comentario de la llamada {self.call_id}"


class ProposalAppointment(models.Model):
    STATUS_CHOICES = [
        ("submitted", "Presentada"),
        ("acceptance_appointment", "Cita de aceptación programada"),
        ("accepted", "Aceptada"),
        ("counteroffer", "Contraoferta recibida"),
        ("contract_appointment", "Cita de contrato programada"),
        ("signing_appointment", "Cita de escrituración programada"),
    ]

    source_sale_appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name="proposal",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="proposals",
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.PROTECT,
        related_name="proposals",
    )
    buyer = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        related_name="purchase_proposals",
    )
    agent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="purchase_proposals",
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="submitted",
    )
    listing_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Precio del encargo",
    )
    offered_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Precio ofertado",
    )
    deposit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Señal entregada",
    )
    proposal_date = models.DateField(verbose_name="Fecha de creación")
    end_date = models.DateField(verbose_name="Fecha final")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Propuesta de compra"
        verbose_name_plural = "Propuestas de compra"

    def __str__(self):
        return f"Propuesta de {self.buyer} para {self.listing.property}"


class CounterOffer(models.Model):
    proposal = models.ForeignKey(
        ProposalAppointment,
        on_delete=models.CASCADE,
        related_name="counteroffers",
    )
    source_acceptance_appointment = models.OneToOneField(
        Appointment,
        on_delete=models.PROTECT,
        related_name="counteroffer",
    )
    counteroffer_date = models.DateField(verbose_name="Fecha de la contraoferta")
    owner_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Precio solicitado por el propietario",
    )
    notes = models.TextField(blank=True, verbose_name="Notas")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-counteroffer_date", "-created_at"]
        verbose_name = "Contraoferta"
        verbose_name_plural = "Contraofertas"

    def __str__(self):
        return f"Contraoferta de {self.owner_price} €"
