from django.db import models


class Property(models.Model):

    PROPERTY_TYPE_CHOICES = (
        ('flat', 'Piso'),
        ('house', 'Casa'),
        ('villa', 'Villa'),
        ('office', 'Oficina'),
    )
    
    STATUS_CHOICES = [
        ("active", "Activo"),
        ("reserved", "Reservado"),
        ("sold", "Vendido"),
    ]

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

    image = models.ImageField(
        upload_to='properties/',
        blank=True,
        null=True
    )

    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )

    def __str__(self):
        return self.title