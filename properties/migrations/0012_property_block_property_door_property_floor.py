from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0011_property_created_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="block",
            field=models.CharField(
                blank=True,
                max_length=30,
                verbose_name="Bloque o portal",
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="door",
            field=models.CharField(
                blank=True,
                max_length=30,
                verbose_name="Puerta o local",
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="floor",
            field=models.CharField(
                blank=True,
                max_length=20,
                verbose_name="Planta",
            ),
        ),
    ]
