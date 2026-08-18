from django.db import migrations, models


def mark_existing_orders_as_purchase(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    Order.objects.filter(operation_type__isnull=True).update(operation_type="sale")


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0004_alter_order_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="operation_type",
            field=models.CharField(
                choices=[("sale", "Compra"), ("rent", "Alquiler")],
                max_length=10,
                null=True,
                verbose_name="Operación",
            ),
        ),
        migrations.RunPython(
            mark_existing_orders_as_purchase,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="order",
            name="operation_type",
            field=models.CharField(
                choices=[("sale", "Compra"), ("rent", "Alquiler")],
                max_length=10,
                verbose_name="Operación",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="property_type",
            field=models.CharField(
                choices=[
                    ("flat", "Piso"),
                    ("house", "Casa"),
                    ("villa", "Villa"),
                    ("office", "Oficina"),
                    ("local", "Local"),
                    ("nave", "Nave"),
                    ("solar", "Solar"),
                    ("terreno", "Terreno"),
                ],
                max_length=20,
                verbose_name="Tipo de inmueble",
            ),
        ),
    ]
