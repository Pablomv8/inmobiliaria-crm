from django.db import models

# Create your models here.
from django.db import models
from properties.models import Property
from django.conf import settings

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

    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contacts'
    )

    def __str__(self):
        return self.name
    
    def status_color(self):
        return {
            'new': 'bg-blue-100 text-blue-700',
            'interested': 'bg-green-100 text-green-700',
            'visit': 'bg-yellow-100 text-yellow-700',
            'negotiation': 'bg-orange-100 text-orange-700',
            'closed': 'bg-gray-200 text-gray-700',
        }.get(self.status, '')