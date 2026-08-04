from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from calendar_app.models import Appointment
from contacts.models import Contact
from news.models import News, NewsComment
from properties.models import Property
from users.models import User


class Command(BaseCommand):
    help = "Crea datos aislados para probar el flujo noticia-cita-encargo"

    username = "demo_flujo"
    password = "DemoCRM2026!"

    @transaction.atomic
    def handle(self, *args, **options):
        agent, _ = User.objects.get_or_create(
            username=self.username,
            defaults={
                "first_name": "Agente",
                "last_name": "Demo",
                "email": "demo.flujo@example.com",
                "role": "agent",
            },
        )
        agent.first_name = "Agente"
        agent.last_name = "Demo"
        agent.role = "agent"
        agent.set_password(self.password)
        agent.save()

        owner = Contact.objects.filter(
            identification_number="DEMO-FLUJO-001"
        ).first()
        if owner is None:
            owner = Contact.objects.create(
                name="Carmen",
                last_name="Propietaria Demo",
                identification_number="DEMO-FLUJO-001",
                phone="600 123 456",
                email="carmen.demo@example.com",
                contact_type="owner",
                assigned_agent=agent,
                notes="Contacto creado para probar el flujo de adquisición.",
            )

        today = timezone.localdate()

        initial_property = self.get_or_create_property(
            street="Calle Demo Inicio",
            number="1",
            city="Madrid",
            property_type="local",
        )
        comment_property = self.get_or_create_property(
            street="Calle Demo Comentario",
            number="2",
            city="Madrid",
            property_type="solar",
        )
        decision_property = self.get_or_create_property(
            street="Calle Demo Decisión",
            number="3",
            city="Madrid",
            property_type="terreno",
        )

        properties = [
            initial_property,
            comment_property,
            decision_property,
        ]
        owner.properties.add(*properties)

        initial_news = self.get_or_create_news(
            initial_property,
            agent,
            client_price="210000.00",
            estimated_price="200000.00",
        )
        comment_news = self.get_or_create_news(
            comment_property,
            agent,
            client_price="165000.00",
            estimated_price="155000.00",
        )
        decision_news = self.get_or_create_news(
            decision_property,
            agent,
            client_price="320000.00",
            estimated_price="305000.00",
        )

        NewsComment.objects.get_or_create(
            news=initial_news,
            text="El propietario muestra interés y acepta concertar una cita.",
            defaults={"user": agent},
        )

        comment_appointment = self.get_or_create_appointment(
            marker="[DEMO] Cita pendiente de comentario",
            news=comment_news,
            owner=owner,
            agent=agent,
            appointment_date=today + timedelta(days=1),
            appointment_time=time(10, 0),
            status="scheduled",
        )

        decision_appointment = self.get_or_create_appointment(
            marker="[DEMO] Cita lista para decidir",
            news=decision_news,
            owner=owner,
            agent=agent,
            appointment_date=today,
            appointment_time=time(11, 0),
            status="completed",
            result_comment=(
                "La reunión se celebró correctamente. El propietario está "
                "esperando la propuesta final de colaboración."
            ),
        )

        self.stdout.write(self.style.SUCCESS("Datos de prueba preparados."))
        self.stdout.write("")
        self.stdout.write(f"Usuario: {self.username}")
        self.stdout.write(f"Contraseña: {self.password}")
        self.stdout.write("")
        self.stdout.write("1. Probar desde una noticia:")
        self.stdout.write(reverse("news_detail", args=[initial_news.pk]))
        self.stdout.write("2. Añadir comentario a una cita:")
        self.stdout.write(
            reverse("appointment_detail", args=[comment_appointment.pk])
        )
        self.stdout.write("3. Decidir si la cita tuvo éxito:")
        self.stdout.write(
            reverse("appointment_detail", args=[decision_appointment.pk])
        )

    def get_or_create_property(self, **data):
        property_obj = Property.objects.filter(
            street=data["street"],
            number=data["number"],
            city=data["city"],
        ).first()

        if property_obj is None:
            property_obj = Property.objects.create(
                **data,
                status="prospect",
                description="Inmueble creado para probar el flujo completo.",
            )

        return property_obj

    def get_or_create_news(
        self,
        property_obj,
        agent,
        client_price,
        estimated_price,
    ):
        news = News.objects.filter(
            related_property=property_obj,
            motivation="sale",
        ).first()

        if news is None:
            news = News.objects.create(
                related_property=property_obj,
                agent=agent,
                motivation="sale",
                client_price=client_price,
                estimated_price=estimated_price,
                status="contacted",
            )

        return news

    def get_or_create_appointment(
        self,
        marker,
        news,
        owner,
        agent,
        appointment_date,
        appointment_time,
        status,
        result_comment="",
    ):
        appointment = Appointment.objects.filter(
            agent=agent,
            notes=marker,
        ).first()

        if appointment is None:
            appointment = Appointment.objects.create(
                related_property=news.related_property,
                contact=owner,
                agent=agent,
                appointment_type="acquisition",
                date=appointment_date,
                time=appointment_time,
                notes=marker,
                status=status,
                news=news,
                result_comment=result_comment,
            )

        return appointment
