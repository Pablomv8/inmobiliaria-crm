from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from contacts.models import Contact
from properties.models import Property, Zone
from django.utils import timezone
from datetime import timedelta


class Task(models.Model):

    TASK_TYPE_CHOICES = (
        ("custom", "Personalizada"),
        ("zone_sweep", "Peinar una zona"),
    )

    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('in_progress', 'En progreso'),
        ('done', 'Completada'),
        ('cancelled', 'Cancelada'),
    )

    PRIORITY_CHOICES = (
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
    )

    task_type = models.CharField(
        max_length=20,
        choices=TASK_TYPE_CHOICES,
        default="custom",
        verbose_name="Tipo de tarea",
    )

    title = models.CharField(max_length=255, blank=True, verbose_name="Nombre")

    description = models.TextField(blank=True)

    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )

    related_property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )

    zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        verbose_name="Zona",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium'
    )

    due_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        errors = {}

        if self.task_type == "custom":
            if not self.title.strip():
                errors["title"] = "Escribe un nombre para la tarea personalizada."
            if not self.description.strip():
                errors["description"] = "Escribe una descripción para la tarea personalizada."
        elif self.task_type == "zone_sweep" and self.zone_id is None:
            errors["zone"] = "Selecciona la zona que se debe peinar."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.task_type == "zone_sweep" and self.zone_id:
            self.title = f"Peinar zona {self.zone.name}"
            self.description = ""
        elif self.task_type == "custom":
            self.zone = None

        return super().save(*args, **kwargs)
    
    @property
    def due_label(self):

        if not self.due_date:
            return "Sin fecha"

        now = timezone.localtime()
        due = timezone.localtime(self.due_date)

        if due.date() == now.date():
            return due.strftime("%H:%M")

        if due.date() == (now + timedelta(days=1)).date():
            return "Mañana"

        return due.strftime("%d %b")
