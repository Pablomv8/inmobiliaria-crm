from django.db import models
from django.core.exceptions import ValidationError

# Create your models here.
from django.db import models

from users.models import User

from contacts.models import Contact
from properties.models import Property
from news.models import News
from config.comment_audit import AuditedComment



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
        ("financial_advice", "Asesoramiento financiero"),
    ]

    STATUS_CHOICES = [
        ("scheduled", "Programada"),
        ("completed", "Completada"),
        ("cancelled", "Cancelada"),
    ]

    FOLLOW_UP_ACTION_CHOICES = [
        ("price_reduction", "Rebaja del encargo"),
        ("renewal", "Renovación del encargo"),
        ("none", "Sin cambios"),
    ]

    related_property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
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

    financial_entity = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Financiera",
    )

    mortgage_capacity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Capacidad hipotecaria estimada (€)",
    )

    follow_up_action = models.CharField(
        max_length=20,
        choices=FOLLOW_UP_ACTION_CHOICES,
        null=True,
        blank=True,
        verbose_name="Acción tras el seguimiento",
    )

    follow_up_previous_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Precio anterior al seguimiento",
    )

    follow_up_new_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Precio tras el seguimiento",
    )

    follow_up_previous_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha límite anterior",
    )

    follow_up_new_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Nueva fecha límite",
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

    class Meta:
        indexes = [
            models.Index(fields=["agent", "status", "date"], name="appt_agent_status_date"),
            models.Index(fields=["status", "date"], name="appt_status_date"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("time")),
                name="appointment_end_after_start",
            ),
        ]

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

    class Meta:
        indexes = [
            models.Index(fields=["agent", "status", "date"], name="call_agent_status_date"),
            models.Index(fields=["status", "date"], name="call_status_date"),
        ]

    def __str__(self):
        return (
            f"Llamada {self.date} a las {self.time}"
        )


class CallComment(AuditedComment):
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
        indexes = [
            models.Index(fields=["agent", "status", "end_date"], name="proposal_agent_status_end"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("proposal_date")),
                name="proposal_end_after_start",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(listing_price__gt=0)
                    & models.Q(offered_price__gt=0)
                    & models.Q(deposit_amount__gte=0)
                ),
                name="proposal_valid_amounts",
            ),
        ]

    def __str__(self):
        return f"Propuesta de {self.buyer} para {self.listing.property}"


class ProposalComment(AuditedComment):
    proposal = models.ForeignKey(
        ProposalAppointment,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposal_comments",
    )
    text = models.TextField(verbose_name="Comentario")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Comentario de propuesta"
        verbose_name_plural = "Comentarios de propuesta"

    def __str__(self):
        return f"Comentario de la propuesta {self.proposal_id}"


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
        constraints = [
            models.CheckConstraint(
                condition=models.Q(owner_price__gt=0),
                name="counteroffer_positive_price",
            ),
        ]

    def __str__(self):
        return f"Contraoferta de {self.owner_price} €"
