from django.db import models, transaction

from properties.models import Property
from users.models import User


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
        is_new = self._state.adding

        if not is_new:
            return super().save(*args, **kwargs)

        with transaction.atomic():
            result = super().save(*args, **kwargs)
            changed = Property.objects.filter(pk=self.related_property_id).exclude(
                status="active"
            ).update(status="active")
            if changed:
                self.related_property.status = "active"
            return result
    

class NewsComment(models.Model):

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
