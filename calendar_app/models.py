from django.db import models

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
        ("signing", "Firma"),
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

    notes = models.TextField(
        blank=True
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

    def __str__(self):
        return (
            f"Llamada {self.date} a las {self.time}"
        )