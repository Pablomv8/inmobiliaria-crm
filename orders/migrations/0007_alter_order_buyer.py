from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("contacts", "0008_remove_contact_contact_type"),
        ("orders", "0006_order_agent"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="buyer",
            field=models.ForeignKey(
                limit_choices_to={"is_buyer": True},
                on_delete=django.db.models.deletion.PROTECT,
                related_name="orders",
                to="contacts.contact",
            ),
        ),
    ]
