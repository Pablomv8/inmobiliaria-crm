from datetime import datetime, time, timedelta

from django.db import migrations, models


def populate_appointment_end_times(apps, schema_editor):
    Appointment = apps.get_model("calendar_app", "Appointment")
    appointments = []
    for appointment in Appointment.objects.filter(end_time__isnull=True):
        start = datetime.combine(appointment.date, appointment.time)
        end = start + timedelta(minutes=30)
        appointment.end_time = (
            end.time()
            if end.date() == appointment.date
            else time(23, 59, 59)
        )
        appointments.append(appointment)

    if appointments:
        Appointment.objects.bulk_update(appointments, ["end_time"])


class Migration(migrations.Migration):
    dependencies = [
        ("calendar_app", "0010_appointment_source_counteroffer"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="end_time",
            field=models.TimeField(
                null=True,
                verbose_name="Hora de fin",
            ),
        ),
        migrations.RunPython(
            populate_appointment_end_times,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="appointment",
            name="end_time",
            field=models.TimeField(verbose_name="Hora de fin"),
        ),
    ]
