from django.db import models
from properties.models import Property
from django.conf import settings


class Contact(models.Model):

    MARITAL_STATUS_CHOICES = [
        ("single", "Soltero/a"),
        ("married", "Casado/a"),
        ("divorced", "Divorciado/a"),
        ("widowed", "Viudo/a"),
        ("partner", "Pareja de hecho"),
        ("other", "Otro"),
    ]

    name = models.CharField(
        max_length=100
    )

    last_name = models.CharField(
        max_length=150,
        blank=True
    )

    phone = models.CharField(
        max_length=20
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    street = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Calle"
    )

    number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Número"
    )

    floor = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Piso / Puerta"
    )

    postal_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Código postal"
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ciudad"
    )

    province = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Provincia"
    )

    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de nacimiento"
    )

    occupation = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Profesión"
    )
        

    identification_number = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="DNI / NIE / Pasaporte"
    )

    marital_status = models.CharField(
        max_length=20,
        choices=MARITAL_STATUS_CHOICES,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    properties = models.ManyToManyField(
        Property,
        related_name="contacts",
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts"
    )
    
    is_owner = models.BooleanField(
        default=False,
        verbose_name="Es propietario",
    )

    is_buyer = models.BooleanField(
        default=False,
        verbose_name="Es comprador",
    )

    is_archived = models.BooleanField(
        default=False,
        verbose_name="Archivado",
    )

    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de archivo",
    )

    class Meta:
        indexes = [
            models.Index(fields=["assigned_agent", "is_archived"], name="contact_agent_archived"),
            models.Index(fields=["identification_number"], name="contact_identity_idx"),
            models.Index(fields=["phone"], name="contact_phone_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_owner=True) | models.Q(is_buyer=True),
                name="contact_has_at_least_one_role",
            ),
        ]

    def get_roles_display(self):
        if self.is_owner and self.is_buyer:
            return "Propietario y comprador"
        if self.is_owner:
            return "Propietario"
        if self.is_buyer:
            return "Comprador"
        return "Sin rol"

    def __str__(self):
        return f"{self.name} {self.last_name}".strip()
