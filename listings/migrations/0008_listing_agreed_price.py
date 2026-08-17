from decimal import Decimal

import django.core.validators
from django.db import migrations, models


def copy_agency_price_to_agreed_price(apps, schema_editor):
    Listing = apps.get_model("listings", "Listing")
    for listing in Listing.objects.all().iterator():
        listing.agreed_price = listing.agency_price
        listing.save(update_fields=["agreed_price"])


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0007_listing_commission_amount"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="agreed_price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=12,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="Precio acordado (€)",
            ),
        ),
        migrations.RunPython(
            copy_agency_price_to_agreed_price,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="listing",
            name="agreed_price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="Precio acordado (€)",
            ),
        ),
    ]
