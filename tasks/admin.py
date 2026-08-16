from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "task_type",
        "zone",
        "assigned_to",
        "priority",
        "status",
        "due_date",
    )
    list_filter = ("task_type", "zone", "priority", "status", "assigned_to")
    search_fields = ("title", "description", "zone__name", "assigned_to__username")
