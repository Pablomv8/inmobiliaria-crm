from django.db import models

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
    

class NewsComment(models.Model):

    news = models.ForeignKey(
        News,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    text = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Comentario {self.id}"
        )