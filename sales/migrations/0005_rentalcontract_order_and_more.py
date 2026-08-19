import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("calendar_app", "0013_proposalcomment"),
        ("orders", "0005_order_operation_type_alter_order_property_type"),
        ("sales", "0004_rentalcontract_sale_closing_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="rentalcontract",
            name="order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="rental_contracts",
                to="orders.order",
                verbose_name="Pedido de origen",
            ),
        ),
        migrations.AddField(
            model_name="rentalcontract",
            name="proposal",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="rental_contracts",
                to="calendar_app.proposalappointment",
                verbose_name="Propuesta aceptada",
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="completed_sales",
                to="orders.order",
                verbose_name="Pedido de origen",
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="proposal",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="completed_sales",
                to="calendar_app.proposalappointment",
                verbose_name="Propuesta aceptada",
            ),
        ),
    ]
