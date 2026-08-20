from django.contrib import admin

from .models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "scope",
        "metric",
        "target_count",
        "start_date",
        "end_date",
        "created_by",
    )
    list_filter = ("scope", "metric", "start_date", "end_date")
    search_fields = ("name", "description", "assignees__username")
    filter_horizontal = ("assignees",)
