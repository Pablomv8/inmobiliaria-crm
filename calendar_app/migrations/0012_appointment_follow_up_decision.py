from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("calendar_app", "0011_appointment_end_time"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="follow_up_action",
            field=models.CharField(
                blank=True,
                choices=[
                    ("price_reduction", "Rebaja del encargo"),
                    ("renewal", "Renovación del encargo"),
                    ("none", "Sin cambios"),
                ],
                max_length=20,
                null=True,
                verbose_name="Acción tras el seguimiento",
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="follow_up_new_end_date",
            field=models.DateField(blank=True, null=True, verbose_name="Nueva fecha límite"),
        ),
        migrations.AddField(
            model_name="appointment",
            name="follow_up_new_price",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="Precio tras el seguimiento"),
        ),
        migrations.AddField(
            model_name="appointment",
            name="follow_up_previous_end_date",
            field=models.DateField(blank=True, null=True, verbose_name="Fecha límite anterior"),
        ),
        migrations.AddField(
            model_name="appointment",
            name="follow_up_previous_price",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="Precio anterior al seguimiento"),
        ),
    ]
