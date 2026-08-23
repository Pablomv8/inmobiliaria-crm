from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0006_task_end_time_task_repeat_days_task_schedule_date_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Street",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255, verbose_name="Calle")),
                ("normalized_name", models.CharField(editable=False, max_length=255)),
                (
                    "municipality",
                    models.CharField(
                        default="Arcos de la Frontera",
                        max_length=100,
                        verbose_name="Municipio",
                    ),
                ),
                (
                    "geometry",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        verbose_name="Geometría GeoJSON",
                    ),
                ),
                ("external_ids", models.JSONField(blank=True, default=list)),
                ("source", models.CharField(default="OpenStreetMap", max_length=50)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddConstraint(
            model_name="street",
            constraint=models.UniqueConstraint(
                fields=("municipality", "normalized_name"),
                name="unique_street_name_per_municipality",
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="streets",
            field=models.ManyToManyField(
                blank=True,
                related_name="tasks",
                to="tasks.street",
                verbose_name="Calles que se deben peinar",
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="task_type",
            field=models.CharField(
                choices=[
                    ("custom", "Personalizada"),
                    ("zone_sweep", "Peinar una zona"),
                    ("street_sweep", "Peinar calles"),
                ],
                default="custom",
                max_length=20,
                verbose_name="Tipo de tarea",
            ),
        ),
    ]
