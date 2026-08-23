from django.contrib import admin

from .models import Street, Task


@admin.register(Street)
class StreetAdmin(admin.ModelAdmin):
    list_display = ("name", "municipality", "source", "updated_at")
    list_filter = ("municipality", "source")
    search_fields = ("name",)


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
    filter_horizontal = ("streets",)
    search_fields = (
        "title",
        "description",
        "zone__name",
        "streets__name",
        "assigned_to__username",
    )
