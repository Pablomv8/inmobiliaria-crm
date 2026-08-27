from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0008_ordercomment_audit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Activo"),
                    (
                        "financial_advice_appointment",
                        "Asesoramiento financiero programado",
                    ),
                    ("sale_appointment", "Cita de venta programada"),
                    ("proposal_appointment", "Cita de propuesta programada"),
                    ("proposal", "Propuesta realizada"),
                    ("acceptance_appointment", "Aceptación programada"),
                    ("counteroffer", "Contraoferta recibida"),
                    ("contract_appointment", "Contrato programado"),
                    ("signing_appointment", "Escrituración programada"),
                    ("closed", "Cerrado"),
                    ("cancelled", "Cancelado"),
                ],
                default="active",
                max_length=30,
            ),
        ),
    ]
