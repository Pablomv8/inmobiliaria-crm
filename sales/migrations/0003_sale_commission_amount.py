from decimal import Decimal, ROUND_HALF_UP

import django.core.validators
from django.db import migrations, models


CENT = Decimal("0.01")
HUNDRED = Decimal("100")


def convert_percent_to_amount(apps, schema_editor):
    Sale = apps.get_model("sales", "Sale")
    for sale in Sale.objects.all().iterator():
        sale.commission_amount = (
            sale.sale_price * sale.commission_amount / HUNDRED
        ).quantize(CENT, rounding=ROUND_HALF_UP)
        sale.save(update_fields=["commission_amount"])


def convert_amount_to_percent(apps, schema_editor):
    Sale = apps.get_model("sales", "Sale")
    for sale in Sale.objects.all().iterator():
        if sale.sale_price:
            sale.commission_amount = (
                sale.commission_amount / sale.sale_price * HUNDRED
            ).quantize(CENT, rounding=ROUND_HALF_UP)
        else:
            sale.commission_amount = Decimal("0.00")
        sale.save(update_fields=["commission_amount"])


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0002_alter_sale_status"),
    ]

    operations = [
        migrations.RenameField(
            model_name="sale",
            old_name="commission_percent",
            new_name="commission_amount",
        ),
        migrations.AlterField(
            model_name="sale",
            name="commission_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Comisión (€)",
            ),
        ),
        migrations.RunPython(
            convert_percent_to_amount,
            convert_amount_to_percent,
        ),
    ]
