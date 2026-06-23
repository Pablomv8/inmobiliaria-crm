from django.db import models


class Zone(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    class Meta:

        ordering = ["name"]

    def __str__(self):

        return self.name

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
        ("rented", "Alquilado"),
        ("prospect", "Borrador")
    ]

    title = models.CharField(max_length=255)

    street = models.CharField(
        max_length=255
    )

    number = models.CharField(
        max_length=20
    )

    postal_code = models.CharField(
        max_length=10,
        blank=True
    )

    city = models.CharField(
        max_length=100
    )

    province = models.CharField(
        max_length=100,
        blank=True
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True
    )

    property_type = models.CharField(
        max_length=20,
        choices=PROPERTY_TYPE_CHOICES
    )

    zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="properties",
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
        default="prospect"
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    bedrooms = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    bathrooms = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    area = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Superficie en m²",
    )

    built_area = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Superficie construida en m²",
    )

    
    
    @property
    def full_address(self):

        return (
            f"{self.street} {self.number}, "
            f"{self.city}"
        )
    
    def __str__(self):
        return self.full_address

