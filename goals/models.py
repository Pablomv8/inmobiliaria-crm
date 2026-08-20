from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Goal(models.Model):
    SCOPE_INDIVIDUAL = "individual"
    SCOPE_TEAM = "team"
    SCOPE_CHOICES = [
        (SCOPE_INDIVIDUAL, "Individual"),
        (SCOPE_TEAM, "Grupal"),
    ]

    METRIC_CHOICES = [
        ("listings", "Encargos"),
        ("orders", "Pedidos"),
        ("news", "Noticias"),
        ("sale_appointments", "Citas de venta"),
        ("acquisition_appointments", "Citas de adquisición"),
        ("follow_up_appointments", "Citas de seguimiento"),
        ("contacts", "Contactos"),
        ("properties", "Inmuebles"),
        ("vacant_properties", "Inmuebles vacíos"),
        ("tenant_properties", "Inmuebles con inquilinos"),
        ("proposals", "Propuestas"),
        ("sales", "Ventas firmadas"),
        ("rentals", "Alquileres firmados"),
    ]

    name = models.CharField(max_length=160, verbose_name="Nombre")
    description = models.TextField(blank=True, verbose_name="Descripción")
    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default=SCOPE_INDIVIDUAL,
        verbose_name="Tipo de objetivo",
    )
    metric = models.CharField(
        max_length=40,
        choices=METRIC_CHOICES,
        verbose_name="Elemento que se debe conseguir",
    )
    target_count = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Cantidad objetivo",
    )
    start_date = models.DateField(verbose_name="Fecha de inicio")
    end_date = models.DateField(verbose_name="Fecha de finalización")
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="goals",
        verbose_name="Agentes participantes",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_goals",
        verbose_name="Creado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]
        verbose_name = "Objetivo"
        verbose_name_plural = "Objetivos"

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({
                "end_date": "La fecha de finalización no puede ser anterior a la fecha de inicio."
            })

    @property
    def period_status(self):
        today = timezone.localdate()
        if today < self.start_date:
            return "upcoming"
        if today > self.end_date:
            return "finished"
        return "active"

    @property
    def period_status_display(self):
        return {
            "upcoming": "Próximo",
            "active": "En curso",
            "finished": "Finalizado",
        }[self.period_status]

    def __str__(self):
        return self.name
