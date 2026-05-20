from django.db import models

# Create your models here.
from django.db import models

class Property(models.Model):

    PROPERTY_TYPE_CHOICES = (
        ('flat', 'Piso'),
        ('house', 'Casa'),
        ('solar', 'Solar'),
        ('office', 'Oficina'),
        ('local', 'Local'),

    )

    title = models.CharField(max_length=255)

    address = models.CharField(max_length=255)

    city = models.CharField(max_length=100)

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    property_type = models.CharField(
        max_length=20,
        choices=PROPERTY_TYPE_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title