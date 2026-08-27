from django.db import models, transaction

from properties.models import Property
from users.models import User
from config.comment_audit import AuditedComment


class News(models.Model):

    MOTIVATION_CHOICES = [
        ("sale", "Venta"),
        ("rent", "Alquiler"),
    ]

    STATUS_CHOICES = [
        ("new", "Nueva"),
        ("contacted", "Contactado"),
        ("follow_up", "Seguimiento"),
        ("appointment", "Cita programada"),
        ("closed", "Cerrada"),
    ]

    related_property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="news"
    )

    agent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news",
    )

    motivation = models.CharField(
        max_length=20,
        choices=MOTIVATION_CHOICES
    )

    client_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    estimated_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    @property
    def price_difference(self):

        return abs(
            self.client_price -
            self.estimated_price
        )

    def __str__(self):
        return f"{self.get_motivation_display()} · {self.related_property}"

    def save(self, *args, **kwargs):
        previous_property_id = None
        if self.pk:
            previous_property_id = News.objects.filter(pk=self.pk).values_list(
                "related_property_id",
                flat=True,
            ).first()

        with transaction.atomic():
            result = super().save(*args, **kwargs)
            property_ids = {
                property_id
                for property_id in [previous_property_id, self.related_property_id]
                if property_id
            }
            for property_obj in Property.objects.filter(pk__in=property_ids):
                property_obj.sync_status()
            return result

    def delete(self, *args, **kwargs):
        property_id = self.related_property_id
        with transaction.atomic():
            result = super().delete(*args, **kwargs)
            property_obj = Property.objects.filter(pk=property_id).first()
            if property_obj:
                property_obj.sync_status()
            return result
    

class NewsComment(AuditedComment):

    news = models.ForeignKey(
        News,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news_comments",
    )

    text = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Comentario {self.id}"
        )
