from django.contrib import admin
from .models import Property, Zone


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):

    list_display = (
        "name",
    )

    search_fields = (
        "name",
    )


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):

    list_display = (
        "street",
        "number",
        "city",
        "zone",
        "property_type",
        "status",
    )

    search_fields = (
        "street",
        "number",
        "city",
    )
