from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("calendar_app", "0014_comment_audit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="appointment",
            name="appointment_type",
            field=models.CharField(
                choices=[
                    ("acquisition", "Adquisición"),
                    ("sale", "Venta"),
                    ("valuation", "Valoración"),
                    ("signing", "Escrituración"),
                    ("follow_up", "Seguimiento"),
                    ("proposal", "Propuesta"),
                    ("proposal_acceptance", "Aceptación de propuesta"),
                    ("contract", "Contrato"),
                    ("financial_advice", "Asesoramiento financiero"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="related_property",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="properties.property",
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="financial_entity",
            field=models.CharField(
                blank=True,
                max_length=150,
                verbose_name="Financiera",
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="mortgage_capacity",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Capacidad hipotecaria estimada (€)",
            ),
        ),
    ]
