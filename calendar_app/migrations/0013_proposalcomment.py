import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("calendar_app", "0012_appointment_follow_up_decision"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProposalComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField(verbose_name="Comentario")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("proposal", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="calendar_app.proposalappointment")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="proposal_comments", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Comentario de propuesta",
                "verbose_name_plural": "Comentarios de propuesta",
                "ordering": ["-created_at"],
            },
        ),
    ]
