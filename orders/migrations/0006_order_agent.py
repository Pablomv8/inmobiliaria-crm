import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def assign_existing_orders(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    orders = list(
        Order.objects.filter(agent__isnull=True).select_related("buyer")
    )
    for order in orders:
        order.agent_id = order.buyer.assigned_agent_id
    if orders:
        Order.objects.bulk_update(orders, ["agent"])


def clear_assigned_agents(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    Order.objects.update(agent=None)


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0005_order_operation_type_alter_order_property_type"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="agent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="orders",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Agente asignado",
            ),
        ),
        migrations.RunPython(assign_existing_orders, clear_assigned_agents),
    ]
