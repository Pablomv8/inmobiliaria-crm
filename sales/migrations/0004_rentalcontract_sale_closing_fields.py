import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("calendar_app", "0013_proposalcomment"),
        ("contacts", "0006_remove_contact_status_contact_birth_date_and_more"),
        ("listings", "0008_listing_agreed_price"),
        ("properties", "0010_alter_property_property_type"),
        ("sales", "0003_sale_commission_amount"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="buyer_commission",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Comisión entregada por el comprador (€)",
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="contract_reference",
            field=models.CharField(
                blank=True,
                max_length=100,
                verbose_name="Referencia del contrato",
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="deposit_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Señal entregada (€)",
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="earnest_money_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Aportación de arras (€)",
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="former_owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="former_property_sales",
                to="contacts.contact",
                verbose_name="Propietario vendedor",
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="listing",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="completed_sales",
                to="listings.listing",
                verbose_name="Encargo de origen",
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="seller_commission",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Comisión entregada por el vendedor (€)",
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="source_contract_appointment",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="completed_sale",
                to="calendar_app.appointment",
                verbose_name="Cita de contrato",
            ),
        ),
        migrations.AlterField(
            model_name="sale",
            name="sale_date",
            field=models.DateField(default=django.utils.timezone.localdate),
        ),
        migrations.CreateModel(
            name="RentalContract",
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
                (
                    "rent_price",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Renta mensual acordada (€)",
                    ),
                ),
                (
                    "deposit_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Fianza o señal entregada (€)",
                    ),
                ),
                (
                    "owner_commission",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Comisión entregada por el propietario (€)",
                    ),
                ),
                (
                    "tenant_commission",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Comisión entregada por el inquilino (€)",
                    ),
                ),
                (
                    "earnest_money_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Garantía o arras adicionales (€)",
                    ),
                ),
                (
                    "contract_date",
                    models.DateField(
                        default=django.utils.timezone.localdate,
                        verbose_name="Fecha del contrato",
                    ),
                ),
                (
                    "start_date",
                    models.DateField(
                        default=django.utils.timezone.localdate,
                        verbose_name="Inicio del alquiler",
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        blank=True,
                        null=True,
                        verbose_name="Fin del alquiler",
                    ),
                ),
                (
                    "contract_reference",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        verbose_name="Referencia del contrato",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("signed", "Firmado"), ("cancelled", "Cancelado")],
                        default="signed",
                        max_length=20,
                    ),
                ),
                (
                    "notes",
                    models.TextField(blank=True, verbose_name="Observaciones"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "agent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rental_contracts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "listing",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rental_contracts",
                        to="listings.listing",
                        verbose_name="Encargo de origen",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rental_contracts_as_owner",
                        to="contacts.contact",
                        verbose_name="Propietario",
                    ),
                ),
                (
                    "related_property",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rental_contracts",
                        to="properties.property",
                    ),
                ),
                (
                    "source_contract_appointment",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="completed_rental_contract",
                        to="calendar_app.appointment",
                        verbose_name="Cita de contrato",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rental_contracts_as_tenant",
                        to="contacts.contact",
                        verbose_name="Inquilino",
                    ),
                ),
            ],
            options={
                "verbose_name": "Contrato de alquiler",
                "verbose_name_plural": "Contratos de alquiler",
                "ordering": ["-contract_date", "-created_at"],
            },
        ),
    ]
