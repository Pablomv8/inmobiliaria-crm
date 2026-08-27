from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contacts", "0008_remove_contact_contact_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="contact",
            name="archived_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Fecha de archivo",
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="is_archived",
            field=models.BooleanField(default=False, verbose_name="Archivado"),
        ),
    ]
