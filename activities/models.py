# activities/models.py

from django.db import models
from django.conf import settings
from tasks.models import Task
from contacts.models import Contact


class Activity(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    contact = models.ForeignKey(
        Contact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities"
    )

    task = models.ForeignKey(
        Task,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities"
    )

    action = models.CharField(max_length=100)

    description = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.description
    
    @property
    def icon(self):

        icons = {
            "task_created": "📝",
            "task_completed": "✅",
            "task_updated": "✏️",
            "contact_created": "👤",
            "contact_updated": "🔄",
            "contact_deleted": "🗑️",
        }

        return icons.get(self.action, "📌")
