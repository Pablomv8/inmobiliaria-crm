from django.db import models

# Create your models here.
from django.db import models
from properties.models import Property

class Contact(models.Model):

    STATUS_CHOICES = (
        ('new', 'Nuevo'),
        ('interested', 'Interesado'),
        ('visit', 'Visita agendada'),
        ('negotiation', 'Negociación'),
        ('closed', 'Cerrado'),
    )

    name = models.CharField(max_length=255)

    phone = models.CharField(max_length=20)

    email = models.EmailField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )

    notes = models.TextField(blank=True)

    properties = models.ManyToManyField(
        Property,
        related_name='contacts',
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name