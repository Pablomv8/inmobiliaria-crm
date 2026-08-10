from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
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

    schedule_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de inicio",
    )

    start_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Hora de inicio",
    )

    end_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Hora de fin",
    )

    repeat_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        verbose_name="Días consecutivos",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.title

    @property
    def schedule_end_date(self):
        if self.schedule_date and self.repeat_days:
            return self.schedule_date + timedelta(days=self.repeat_days - 1)
        return self.schedule_date

    def clean(self):
        super().clean()
        errors = {}

        if self.task_type == "custom":
            if not self.title.strip():
                errors["title"] = "Escribe un nombre para la tarea personalizada."
            if not self.description.strip():
                errors["description"] = "Escribe una descripción para la tarea personalizada."
            if self.due_date is None:
                errors["due_date"] = (
                    "Selecciona la fecha límite para mostrar la tarea en la agenda."
                )
        elif self.task_type == "zone_sweep":
            if self.zone_id is None:
                errors["zone"] = "Selecciona la zona que se debe peinar."
            if self.schedule_date is None:
                errors["schedule_date"] = "Selecciona la fecha de inicio."
            if self.start_time is None:
                errors["start_time"] = "Selecciona la hora de inicio."
            if self.end_time is None:
                errors["end_time"] = "Selecciona la hora de fin."
            if self.repeat_days is None:
                errors["repeat_days"] = "Selecciona durante cuántos días se repite."
            if (
                self.start_time is not None
                and self.end_time is not None
                and self.end_time <= self.start_time
            ):
                errors["end_time"] = (
                    "La hora de fin debe ser posterior a la hora de inicio."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.task_type == "zone_sweep" and self.zone_id:
            self.title = f"Peinar zona {self.zone.name}"
            self.description = ""
            self.due_date = None
        elif self.task_type == "custom":
            self.zone = None
            self.schedule_date = None
            self.start_time = None
            self.end_time = None
            self.repeat_days = None

        return super().save(*args, **kwargs)
    
    @property
    def due_label(self):

        if self.task_type == "zone_sweep":
            if not self.schedule_date or not self.start_time:
                return "Sin horario"
            if self.schedule_date == timezone.localdate():
                return self.start_time.strftime("%H:%M")
            return self.schedule_date.strftime("%d %b")

        if not self.due_date:
            return "Sin fecha"

        now = timezone.localtime()
        due = timezone.localtime(self.due_date)

        if due.date() == now.date():
            return due.strftime("%H:%M")

        if due.date() == (now + timedelta(days=1)).date():
            return "Mañana"

        return due.strftime("%d %b")
