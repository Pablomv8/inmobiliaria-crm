from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("calendar_app", "0013_proposalcomment"),
    ]

    operations = [
        migrations.AddField(model_name="callcomment", name="edited_at", field=models.DateTimeField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="callcomment", name="hidden_at", field=models.DateTimeField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="callcomment", name="hidden_by", field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="callcomment", name="is_hidden", field=models.BooleanField(default=False, editable=False)),
        migrations.AddField(model_name="callcomment", name="original_text", field=models.TextField(blank=True, editable=False)),
        migrations.AddField(model_name="proposalcomment", name="edited_at", field=models.DateTimeField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="proposalcomment", name="hidden_at", field=models.DateTimeField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="proposalcomment", name="hidden_by", field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="proposalcomment", name="is_hidden", field=models.BooleanField(default=False, editable=False)),
        migrations.AddField(model_name="proposalcomment", name="original_text", field=models.TextField(blank=True, editable=False)),
    ]
