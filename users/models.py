from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    ROLE_CHOICES = (
        ('admin', 'Administrador'),
        ('manager', 'Manager'),
        ('agent', 'Agente'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='agent'
    )

    phone = models.CharField(max_length=20, blank=True)