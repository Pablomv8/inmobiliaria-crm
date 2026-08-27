from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("orders", "0007_alter_order_buyer"),
    ]

    operations = [
        migrations.AddField(model_name="ordercomment", name="edited_at", field=models.DateTimeField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="ordercomment", name="hidden_at", field=models.DateTimeField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name="ordercomment", name="hidden_by", field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="ordercomment", name="is_hidden", field=models.BooleanField(default=False, editable=False)),
        migrations.AddField(model_name="ordercomment", name="original_text", field=models.TextField(blank=True, editable=False)),
    ]
