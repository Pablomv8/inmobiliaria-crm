from django.db import migrations, models


def copy_contact_roles(apps, schema_editor):
    Contact = apps.get_model("contacts", "Contact")
    Contact.objects.filter(contact_type="owner").update(is_owner=True)
    Contact.objects.filter(contact_type="buyer").update(is_buyer=True)


def restore_contact_type(apps, schema_editor):
    Contact = apps.get_model("contacts", "Contact")
    Contact.objects.filter(is_owner=True).update(contact_type="owner")
    Contact.objects.filter(is_owner=False, is_buyer=True).update(
        contact_type="buyer",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("contacts", "0006_remove_contact_status_contact_birth_date_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="contact",
            name="is_buyer",
            field=models.BooleanField(default=False, verbose_name="Es comprador"),
        ),
        migrations.AddField(
            model_name="contact",
            name="is_owner",
            field=models.BooleanField(default=False, verbose_name="Es propietario"),
        ),
        migrations.RunPython(copy_contact_roles, restore_contact_type),
        migrations.AddConstraint(
            model_name="contact",
            constraint=models.CheckConstraint(
                condition=models.Q(is_owner=True) | models.Q(is_buyer=True),
                name="contact_has_at_least_one_role",
            ),
        ),
    ]
