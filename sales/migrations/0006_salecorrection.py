from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("sales", "0005_rentalcontract_order_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SaleCorrection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.TextField(verbose_name="Motivo de la corrección")),
                ("previous_values", models.JSONField()),
                ("new_values", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("corrected_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sale_corrections", to=settings.AUTH_USER_MODEL)),
                ("sale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="corrections", to="sales.sale")),
            ],
            options={"verbose_name": "Corrección de compraventa", "verbose_name_plural": "Correcciones de compraventas", "ordering": ["-created_at"]},
        ),
    ]
