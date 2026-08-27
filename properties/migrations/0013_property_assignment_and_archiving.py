from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_property_responsible(apps, schema_editor):
    Property = apps.get_model("properties", "Property")
    Property.objects.filter(created_by__isnull=False).update(
        assigned_agent_id=models.F("created_by_id"),
    )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("properties", "0012_property_block_property_door_property_floor"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="archived_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Fecha de archivo",
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="assigned_agent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_properties",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Agente responsable",
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="is_archived",
            field=models.BooleanField(default=False, verbose_name="Archivado"),
        ),
        migrations.RunPython(copy_property_responsible, migrations.RunPython.noop),
    ]
