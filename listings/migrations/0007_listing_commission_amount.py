from decimal import Decimal, ROUND_HALF_UP

import django.core.validators
from django.db import migrations, models


CENT = Decimal("0.01")
HUNDRED = Decimal("100")


def convert_percent_to_amount(apps, schema_editor):
    Listing = apps.get_model("listings", "Listing")
    for listing in Listing.objects.exclude(commission_amount__isnull=True).iterator():
        listing.commission_amount = (
            listing.agency_price * listing.commission_amount / HUNDRED
        ).quantize(CENT, rounding=ROUND_HALF_UP)
        listing.save(update_fields=["commission_amount"])


def convert_amount_to_percent(apps, schema_editor):
    Listing = apps.get_model("listings", "Listing")
    for listing in Listing.objects.exclude(commission_amount__isnull=True).iterator():
        if listing.agency_price:
            listing.commission_amount = (
                listing.commission_amount / listing.agency_price * HUNDRED
            ).quantize(CENT, rounding=ROUND_HALF_UP)
        else:
            listing.commission_amount = Decimal("0.00")
        listing.save(update_fields=["commission_amount"])


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0006_alter_listing_workflow_status"),
    ]

    operations = [
        migrations.RenameField(
            model_name="listing",
            old_name="commission_percent",
            new_name="commission_amount",
        ),
        migrations.AlterField(
            model_name="listing",
            name="commission_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Comisión acordada (€)",
            ),
        ),
        migrations.RunPython(
            convert_percent_to_amount,
            convert_amount_to_percent,
        ),
    ]
