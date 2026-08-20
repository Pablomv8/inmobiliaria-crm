from django.db import models
from django.db.models import Max
from django.utils import timezone
from django.conf import settings

from datetime import timedelta


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
        ('local', 'Local'),
        ('nave', 'Nave'),
        ('solar', 'Solar'),
        ('terreno', 'Terreno'),
    )

    STATUS_CHOICES = [
        ("news", "Noticia"),
        ("never_contacted", "Nunca contactado"),
        ("contacted", "Contactado"),
        ("contacted_30", "Contactado hace más de 30 días"),
        ("vacant", "Vacío"),
        ("in_listing", "En encargo"),
        ("sold", "Vendido"),
        ("rented", "Alquilado"),
    ]

    OCCUPANCY_CHOICES = [
        ("vacant", "Vacío"),
        ("owner", "Propietario"),
        ("tenants", "Inquilinos"),
    ]

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

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_properties",
        verbose_name="Creado por",
    )


    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="never_contacted",
        editable=False,
    )

    occupied_by = models.CharField(
        max_length=20,
        choices=OCCUPANCY_CHOICES,
        default="owner",
        verbose_name="Ocupado por",
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

    def calculate_status(self):
        if self.pk:
            if self.sales.filter(status="signed").exists():
                return "sold"

            if self.listings.filter(status="sold").exists():
                return "sold"

            if self.listings.filter(status="rented").exists():
                return "rented"

            if self.listings.filter(status="active").exists():
                return "in_listing"

            if self.news.exists():
                return "news"

        if self.occupied_by == "tenants":
            return "rented"

        if self.occupied_by == "vacant":
            return "vacant"

        latest_comment = self.comments.order_by("-created_at").first() if self.pk else None
        if latest_comment is None:
            return "never_contacted"

        if latest_comment.created_at < timezone.now() - timedelta(days=30):
            return "contacted_30"

        return "contacted"

    def sync_status(self):
        calculated_status = self.calculate_status()
        if self.status != calculated_status:
            previous_status = self.status
            self.__class__.objects.filter(pk=self.pk).update(
                status=calculated_status,
            )
            self.status = calculated_status
            PropertyStatusHistory.objects.create(
                property=self,
                old_status=previous_status,
                new_status=calculated_status,
            )
        return calculated_status

    @classmethod
    def refresh_aged_contact_statuses(cls):
        threshold = timezone.now() - timedelta(days=30)
        properties = cls.objects.filter(status="contacted").annotate(
            latest_comment=Max("comments__created_at"),
        ).filter(
            latest_comment__lt=threshold,
        )
        refreshed = 0
        for property_obj in properties:
            if property_obj.sync_status() == "contacted_30":
                refreshed += 1
        return refreshed

    def save(self, *args, **kwargs):
        previous_status = None
        if self.pk:
            previous_status = self.__class__.objects.filter(pk=self.pk).values_list(
                "status",
                flat=True,
            ).first()
        self.status = self.calculate_status()
        result = super().save(*args, **kwargs)
        if previous_status is not None and previous_status != self.status:
            PropertyStatusHistory.objects.create(
                property=self,
                old_status=previous_status,
                new_status=self.status,
            )
        return result

    
    
    @property
    def full_address(self):

        return (
            f"{self.street} {self.number}, "
            f"{self.city}"
        )
    
    def __str__(self):
        return self.full_address


class PropertyComment(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="property_comments",
    )
    text = models.TextField(verbose_name="Comentario")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Comentario de inmueble"
        verbose_name_plural = "Comentarios de inmuebles"

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        self.property.sync_status()
        return result

    def delete(self, *args, **kwargs):
        property_obj = self.property
        result = super().delete(*args, **kwargs)
        property_obj.sync_status()
        return result

    def __str__(self):
        return f"Comentario del inmueble {self.property_id}"


class PropertyStatusHistory(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    old_status = models.CharField(
        max_length=30,
        choices=Property.STATUS_CHOICES,
        blank=True,
        verbose_name="Estado anterior",
    )
    new_status = models.CharField(
        max_length=30,
        choices=Property.STATUS_CHOICES,
        verbose_name="Estado nuevo",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Cambio de estado de inmueble"
        verbose_name_plural = "Cambios de estado de inmuebles"

    def __str__(self):
        return (
            f"{self.property}: {self.get_old_status_display()} → "
            f"{self.get_new_status_display()}"
        )

