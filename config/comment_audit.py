from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditedComment(models.Model):
    """Campos comunes para corregir comentarios sin perder el original."""

    original_text = models.TextField(blank=True, editable=False)
    edited_at = models.DateTimeField(null=True, blank=True, editable=False)
    is_hidden = models.BooleanField(default=False, editable=False)
    hidden_at = models.DateTimeField(null=True, blank=True, editable=False)
    hidden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        editable=False,
    )

    class Meta:
        abstract = True

    @property
    def display_text(self):
        if self.is_hidden:
            return "Comentario ocultado por moderación."
        return self.text

    @property
    def is_editable(self):
        return (
            not self.is_hidden
            and self.user_id is not None
            and timezone.now() <= self.created_at + timedelta(minutes=15)
        )

    def can_be_edited_by(self, user):
        return bool(user and user.is_authenticated and self.user_id == user.pk and self.is_editable)
