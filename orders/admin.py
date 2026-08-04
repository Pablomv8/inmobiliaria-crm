from django.contrib import admin

from .models import Order, OrderComment


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "buyer",
        "property_type",
        "max_price",
        "payment_type",
        "zone",
        "created_at",
    )
    search_fields = ("buyer__name", "buyer__last_name", "buyer__phone")
    list_filter = ("payment_type", "property_type", "zone")


@admin.register(OrderComment)
class OrderCommentAdmin(admin.ModelAdmin):
    list_display = ("order", "user", "created_at")
    search_fields = ("text", "order__buyer__name")
