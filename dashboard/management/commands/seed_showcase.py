import io
import os
import secrets
from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from calendar_app.models import Appointment, Call, ProposalAppointment
from contacts.models import Contact
from goals.models import Goal
from listings.models import Listing, ListingComment
from news.models import News, NewsComment
from orders.models import Order, OrderComment
from properties.models import Property, PropertyComment, Zone
from sales.models import RentalContract, Sale
from tasks.models import Street, Task
from users.models import User


class Command(BaseCommand):
    help = (
        "Prepara una demostración integral, idempotente y aislada del CRM. "
        "No elimina información ajena a la demostración."
    )

    marker = "[DEMO PRESENTACION]"
    workflow_marker = "[DEMO FLUJO INTEGRAL]"
    operations_marker = "[DEMO OPERACIONES]"
    demo_usernames = (
        "admin_demo",
        "pablo",
        "carlos",
        "marta",
        "demo_flujo_integral",
        "demo_operaciones",
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-password",
            help=(
                "Contraseña para manager y agentes. Es preferible usar la "
                "variable DEMO_SEED_PASSWORD para no dejarla en el historial."
            ),
        )
        parser.add_argument(
            "--admin-password",
            help=(
                "Contraseña del superusuario. Es preferible usar la variable "
                "DEMO_ADMIN_PASSWORD."
            ),
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            help="Elimina exclusivamente los registros reconocibles de esta demo.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["purge"]:
            self.purge_demo()
            return

        user_password, generated_user_password = self.resolve_password(
            options["user_password"],
            "DEMO_SEED_PASSWORD",
        )
        admin_password, generated_admin_password = self.resolve_password(
            options["admin_password"],
            "DEMO_ADMIN_PASSWORD",
        )
        if user_password == admin_password:
            raise CommandError(
                "La contraseña del superusuario debe ser distinta de la de los "
                "usuarios de demostración."
            )

        users = self.create_primary_users(user_password, admin_password)

        # Estos comandos ya contienen los escenarios complejos del flujo y son
        # idempotentes. Se silencia su salida porque mostraban credenciales antiguas.
        hidden_output = io.StringIO()
        call_command("seed_full_workflow", stdout=hidden_output, verbosity=0)
        call_command("seed_sales_rentals", stdout=hidden_output, verbosity=0)

        self.secure_auxiliary_agents(user_password)
        self.create_arcos_showcase(users)
        call_command("seed_goals", stdout=hidden_output, verbosity=0)

        self.print_summary(
            user_password,
            admin_password,
            generated_user_password,
            generated_admin_password,
        )

    def resolve_password(self, option_value, environment_key):
        supplied_value = option_value or os.getenv(environment_key, "").strip()
        generated = not supplied_value
        password = supplied_value or secrets.token_urlsafe(18)
        if len(password) < 12:
            raise CommandError(
                f"{environment_key} debe contener al menos 12 caracteres."
            )
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc
        return password, generated

    def create_primary_users(self, user_password, admin_password):
        definitions = {
            "admin": {
                "username": "admin_demo",
                "first_name": "Administración",
                "last_name": "Demo CRM",
                "email": "admin.demo@example.com",
                "role": "admin",
                "is_staff": True,
                "is_superuser": True,
                "password": admin_password,
            },
            "manager": {
                "username": "pablo",
                "first_name": "Pablo",
                "last_name": "Manager Demo",
                "email": "pablo.manager.demo@example.com",
                "role": "manager",
                "is_staff": False,
                "is_superuser": False,
                "password": user_password,
            },
            "carlos": {
                "username": "carlos",
                "first_name": "Carlos",
                "last_name": "Agente Demo",
                "email": "carlos.agente.demo@example.com",
                "role": "agent",
                "is_staff": False,
                "is_superuser": False,
                "password": user_password,
            },
            "marta": {
                "username": "marta",
                "first_name": "Marta",
                "last_name": "Agente Demo",
                "email": "marta.agente.demo@example.com",
                "role": "agent",
                "is_staff": False,
                "is_superuser": False,
                "password": user_password,
            },
        }

        users = {}
        for key, values in definitions.items():
            username = values["username"]
            user, created = User.objects.get_or_create(
                username=username,
                defaults={field: value for field, value in values.items() if field != "password"},
            )
            expected_demo_email = values["email"]
            is_managed_demo_user = created or user.email == expected_demo_email
            if not is_managed_demo_user:
                raise CommandError(
                    f"Ya existe el usuario '{username}' y no pertenece a esta demo. "
                    "No se ha modificado su cuenta."
                )
            for field, value in values.items():
                if field not in {"username", "password"}:
                    setattr(user, field, value)
            user.is_active = True
            user.set_password(values["password"])
            user.save()
            users[key] = user
        return users

    def secure_auxiliary_agents(self, password):
        definitions = {
            "demo_flujo_integral": (
                "Agente",
                "Flujo Integral",
                "demo.integral@example.com",
            ),
            "demo_operaciones": (
                "Agente",
                "Operaciones Demo",
                "operaciones.demo@example.com",
            ),
        }
        for username, (first_name, last_name, email) in definitions.items():
            user = User.objects.get(username=username)
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.role = "agent"
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
            user.set_password(password)
            user.save()

    def create_arcos_showcase(self, users):
        today = timezone.localdate()
        manager = users["manager"]
        carlos = users["carlos"]
        marta = users["marta"]

        centre, _ = Zone.objects.update_or_create(
            name="Zona Demo Arcos · Centro histórico",
            defaults={"description": f"{self.marker} Centro y casco histórico."},
        )
        south, _ = Zone.objects.update_or_create(
            name="Zona Demo Arcos · Barrio Bajo",
            defaults={"description": f"{self.marker} Entorno del Barrio Bajo."},
        )

        owner_news = self.upsert_contact(
            "DEMO-SHOW-OWNER-01",
            name="Rocío",
            last_name="Benítez García",
            phone="611 204 318",
            email="rocio.benitez.demo@example.com",
            is_owner=True,
            assigned_agent=carlos,
            notes=f"{self.marker} Propietaria interesada en vender.",
        )
        owner_listing = self.upsert_contact(
            "DEMO-SHOW-OWNER-02",
            name="Antonio",
            last_name="Romero Pérez",
            phone="622 315 429",
            email="antonio.romero.demo@example.com",
            is_owner=True,
            is_buyer=True,
            assigned_agent=manager,
            notes=f"{self.marker} Propietario que también busca otra vivienda.",
        )
        buyer = self.upsert_contact(
            "DEMO-SHOW-BUYER-01",
            name="Sofía",
            last_name="Gómez Ruiz",
            phone="633 426 530",
            email="sofia.gomez.demo@example.com",
            is_buyer=True,
            assigned_agent=marta,
            notes=f"{self.marker} Compradora con financiación preconcedida.",
        )

        property_news = self.upsert_property(
            street="Corredera",
            number="18",
            zone=centre,
            property_type="flat",
            occupied_by="owner",
            latitude=Decimal("36.748350"),
            longitude=Decimal("-5.806250"),
            bedrooms=3,
            bathrooms=2,
            area=96,
            created_by=carlos,
            assigned_agent=carlos,
        )
        property_listing = self.upsert_property(
            street="Avenida Miguel Mancheño",
            number="24",
            zone=south,
            property_type="house",
            occupied_by="vacant",
            latitude=Decimal("36.751250"),
            longitude=Decimal("-5.812150"),
            bedrooms=4,
            bathrooms=2,
            area=165,
            created_by=manager,
            assigned_agent=manager,
        )
        property_vacant = self.upsert_property(
            street="Matrera",
            number="7",
            zone=centre,
            property_type="local",
            occupied_by="vacant",
            latitude=Decimal("36.744950"),
            longitude=Decimal("-5.803450"),
            bathrooms=1,
            area=72,
            created_by=marta,
            assigned_agent=marta,
        )
        owner_news.properties.add(property_news)
        owner_listing.properties.add(property_listing)

        PropertyComment.objects.get_or_create(
            property=property_vacant,
            text=f"{self.marker} Local vacío comprobado durante el peinado de la zona.",
            defaults={"user": marta},
        )

        news, _ = News.objects.update_or_create(
            related_property=property_news,
            motivation="sale",
            defaults={
                "agent": carlos,
                "client_price": Decimal("225000.00"),
                "estimated_price": Decimal("214000.00"),
                "status": "appointment",
            },
        )
        NewsComment.objects.get_or_create(
            news=news,
            text=f"{self.marker} Primera conversación positiva con la propietaria.",
            defaults={"user": carlos},
        )

        listing, _ = Listing.objects.update_or_create(
            property=property_listing,
            listing_type="sale",
            defaults={
                "status": "active",
                "workflow_status": "follow_up_appointment",
                "owner_price": Decimal("278000.00"),
                "agency_price": Decimal("289000.00"),
                "agreed_price": Decimal("285000.00"),
                "price_diference": Decimal("11000.00"),
                "is_exclusive": True,
                "start_date": today - timedelta(days=18),
                "end_date": today + timedelta(days=162),
                "commission_amount": Decimal("9500.00"),
                "owner": owner_listing,
                "agent": manager,
            },
        )
        ListingComment.objects.get_or_create(
            listing=listing,
            text=f"{self.marker} Reportaje preparado y anuncio publicado.",
            defaults={"user": manager},
        )

        order, _ = Order.objects.update_or_create(
            buyer=buyer,
            operation_type="sale",
            notes=f"{self.marker} Busca vivienda familiar con patio o terraza.",
            defaults={
                "agent": marta,
                "status": "financial_advice_appointment",
                "zone": centre,
                "max_price": Decimal("310000.00"),
                "payment_type": "financing",
                "property_type": "house",
                "bedrooms": 3,
                "bathrooms": 2,
            },
        )
        OrderComment.objects.get_or_create(
            order=order,
            text=f"{self.marker} Puede aportar aproximadamente el 25 % del precio.",
            defaults={"user": marta},
        )

        self.upsert_appointment(
            agent=carlos,
            notes=f"{self.marker} Cita de adquisición en Corredera",
            contact=owner_news,
            related_property=property_news,
            appointment_type="acquisition",
            date=today + timedelta(days=1),
            start=time(10, 0),
            end=time(11, 0),
            news=news,
        )
        self.upsert_appointment(
            agent=manager,
            notes=f"{self.marker} Seguimiento del encargo de Miguel Mancheño",
            contact=owner_listing,
            related_property=property_listing,
            appointment_type="follow_up",
            date=today + timedelta(days=3),
            start=time(12, 0),
            end=time(12, 45),
            listing=listing,
        )
        self.upsert_appointment(
            agent=marta,
            notes=f"{self.marker} Asesoramiento hipotecario con la financiera",
            contact=buyer,
            related_property=None,
            appointment_type="financial_advice",
            date=today + timedelta(days=2),
            start=time(17, 0),
            end=time(18, 0),
            order=order,
            financial_entity="Financiera Demo Cádiz",
            mortgage_capacity=Decimal("245000.00"),
        )
        Call.objects.update_or_create(
            agent=carlos,
            notes=f"{self.marker} Confirmar documentación de la noticia",
            defaults={
                "contact": owner_news,
                "date": today + timedelta(days=2),
                "time": time(13, 0),
                "status": "pending",
                "news": news,
            },
        )

        Task.objects.update_or_create(
            title=f"{self.marker} Preparar valoración comparativa",
            defaults={
                "task_type": "custom",
                "description": "Revisar testigos de la zona antes de la captación.",
                "assigned_to": carlos,
                "created_by": manager,
                "status": "in_progress",
                "priority": "high",
                "due_date": timezone.now() + timedelta(days=1, hours=2),
                "contact": owner_news,
                "related_property": property_news,
            },
        )
        Task.objects.update_or_create(
            task_type="zone_sweep",
            zone=south,
            assigned_to=marta,
            defaults={
                "created_by": manager,
                "status": "pending",
                "priority": "medium",
                "schedule_date": today + timedelta(days=1),
                "start_time": time(9, 0),
                "end_time": time(11, 0),
                "repeat_days": 3,
            },
        )
        street_task, _ = Task.objects.update_or_create(
            title=f"{self.marker} Peinar Corredera y Matrera",
            defaults={
                "task_type": "street_sweep",
                "assigned_to": manager,
                "created_by": manager,
                "status": "pending",
                "priority": "medium",
                "schedule_date": today + timedelta(days=2),
                "start_time": time(16, 0),
                "end_time": time(18, 0),
                "repeat_days": 2,
            },
        )
        streets = [
            Street.objects.get_or_create(
                name=name,
                municipality="Arcos de la Frontera",
            )[0]
            for name in ("Corredera", "Matrera")
        ]
        street_task.streets.set(streets)

    def upsert_contact(self, identification_number, **values):
        contact = Contact.objects.filter(
            identification_number=identification_number,
        ).first()
        if contact is None:
            return Contact.objects.create(
                identification_number=identification_number,
                **values,
            )
        for field, value in values.items():
            setattr(contact, field, value)
        contact.save()
        return contact

    def upsert_property(self, street, number, zone, **values):
        property_obj, _ = Property.objects.update_or_create(
            street=street,
            number=number,
            city="Arcos de la Frontera",
            defaults={
                "province": "Cádiz",
                "postal_code": "11630",
                "zone": zone,
                "description": f"{self.marker} Inmueble geolocalizado para la demo.",
                **values,
            },
        )
        return property_obj

    def upsert_appointment(
        self,
        *,
        agent,
        notes,
        contact,
        related_property,
        appointment_type,
        date,
        start,
        end,
        **extra,
    ):
        appointment, _ = Appointment.objects.update_or_create(
            agent=agent,
            notes=notes,
            defaults={
                "contact": contact,
                "related_property": related_property,
                "appointment_type": appointment_type,
                "date": date,
                "time": start,
                "end_time": end,
                "status": "scheduled",
                **extra,
            },
        )
        return appointment

    def purge_demo(self):
        demo_property_filter = Q(description__startswith=self.marker) | Q(
            street__startswith="Demo "
        )
        demo_contact_filter = Q(identification_number__startswith="DEMO-")
        demo_appointment_filter = (
            Q(notes__startswith=self.marker)
            | Q(notes__startswith=self.workflow_marker)
            | Q(notes__startswith=self.operations_marker)
        )

        Sale.objects.filter(
            Q(contract_reference__startswith="CV-DEMO-")
            | Q(notes__startswith=self.marker)
            | Q(notes__startswith=self.operations_marker)
        ).delete()
        RentalContract.objects.filter(
            Q(contract_reference__startswith="ALQ-DEMO-")
            | Q(notes__startswith=self.marker)
            | Q(notes__startswith=self.operations_marker)
        ).delete()
        Goal.objects.filter(name__startswith="[DEMO]").delete()
        ProposalAppointment.objects.filter(
            source_sale_appointment__notes__startswith=self.workflow_marker,
        ).delete()
        Appointment.objects.filter(demo_appointment_filter).delete()
        Call.objects.filter(
            Q(notes__startswith=self.marker)
            | Q(notes__startswith=self.workflow_marker)
            | Q(notes__startswith=self.operations_marker)
        ).delete()
        Task.objects.filter(
            Q(title__startswith=self.marker)
            | Q(zone__name__startswith="Zona Demo")
        ).delete()
        News.objects.filter(related_property__in=Property.objects.filter(demo_property_filter)).delete()
        Listing.objects.filter(property__in=Property.objects.filter(demo_property_filter)).delete()
        Order.objects.filter(
            Q(notes__startswith=self.marker)
            | Q(notes__startswith=self.operations_marker)
            | Q(buyer__identification_number__startswith="DEMO-")
        ).delete()
        Property.objects.filter(demo_property_filter).delete()
        Contact.objects.filter(demo_contact_filter).delete()

        for zone in Zone.objects.filter(name__startswith="Zona Demo"):
            if not zone.properties.exists() and not zone.tasks.exists():
                zone.delete()

        demo_emails = {
            "admin.demo@example.com",
            "pablo.manager.demo@example.com",
            "carlos.agente.demo@example.com",
            "marta.agente.demo@example.com",
            "demo.integral@example.com",
            "operaciones.demo@example.com",
        }
        demo_users = User.objects.filter(
            username__in=self.demo_usernames,
            email__in=demo_emails,
        )
        try:
            with transaction.atomic():
                deleted_users = demo_users.count()
                demo_users.delete()
        except ProtectedError:
            deleted_users = 0
            demo_users.update(is_active=False)
            self.stdout.write(
                self.style.WARNING(
                    "Alguna cuenta demo conserva relaciones protegidas y se ha "
                    "desactivado en lugar de eliminarse."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Datos de demostración retirados. "
                f"Cuentas eliminadas: {deleted_users}."
            )
        )

    def print_summary(
        self,
        user_password,
        admin_password,
        generated_user_password,
        generated_admin_password,
    ):
        self.stdout.write(self.style.SUCCESS("Demostración integral preparada."))
        self.stdout.write("")
        self.stdout.write("Accesos:")
        self.stdout.write("- Superusuario: admin_demo")
        self.stdout.write("- Manager: pablo")
        self.stdout.write("- Agentes: carlos, marta")
        self.stdout.write("- Escenarios auxiliares: demo_flujo_integral, demo_operaciones")
        self.stdout.write(f"- Contraseña del superusuario: {admin_password}")
        self.stdout.write(f"- Contraseña del resto de usuarios: {user_password}")
        if generated_user_password or generated_admin_password:
            self.stdout.write(
                self.style.WARNING(
                    "Guarda ahora las contraseñas generadas: no se podrán consultar "
                    "después desde Django."
                )
            )
        self.stdout.write("")
        self.stdout.write(
            "Incluye datos de Arcos geolocalizados, contactos, noticias, encargos, "
            "pedidos, citas, llamadas, tareas, objetivos, propuestas, ventas y alquileres."
        )
        self.stdout.write("Para retirarlos: python manage.py seed_showcase --purge")
