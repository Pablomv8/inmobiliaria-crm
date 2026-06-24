from django.db import models
from django.conf import settings
from contacts.models import Contact
from properties.models import Property
from django.utils import timezone
from datetime import timedelta


class Task(models.Model):

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

    title = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='tasks'
    )

    related_property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
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