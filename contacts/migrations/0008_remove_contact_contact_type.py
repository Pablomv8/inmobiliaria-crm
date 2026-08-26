from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("contacts", "0007_contact_independent_roles"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="contact",
            name="contact_type",
        ),
    ]
