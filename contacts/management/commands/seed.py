from django.core.management.base import BaseCommand

from contacts.models import Contact
from properties.models import Property
from tasks.models import Task
from django.contrib.auth import get_user_model

from datetime import datetime, timedelta
from django.utils import timezone


class Command(BaseCommand):

    help = 'Populate database with demo data'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        self.stdout.write(self.style.WARNING('Deleting old data...'))

        Task.objects.all().delete()
        Contact.objects.all().delete()
        Property.objects.all().delete()
        User = get_user_model()
        User.objects.filter(is_superuser=False).delete()

        self.stdout.write(self.style.SUCCESS('Creating properties...'))

        p1 = Property.objects.create(
            street="Gran Vía",
            number="123",
            city="Madrid",
            property_type="local"
        )

        p2 = Property.objects.create(
            street="Calle Colón",
            number="45",
            city="Valencia",
            property_type="solar"
        )

        p3 = Property.objects.create(
            street="Avenida Sur",
            number="77",
            city="Sevilla",
            property_type="terreno"
        )

        p4 = Property.objects.create(
            street="Diagonal",
            number="100",
            city="Barcelona",
            property_type="local"
        )

        self.stdout.write(self.style.SUCCESS('Creating contacts...'))

        c1 = Contact.objects.create(
            name="Juan Pérez",
            phone="600111222",
            email="juan@test.com",
            is_owner=True,
        )

        c2 = Contact.objects.create(
            name="Laura Gómez",
            phone="611333444",
            email="laura@test.com",
            is_owner=True,
            is_buyer=True,
        )

        c3 = Contact.objects.create(
            name="Pedro Ruiz",
            phone="699888777",
            email="pedro@test.com",
            is_buyer=True,
        )

        c4 = Contact.objects.create(
            name="Ana Torres",
            phone="644222111",
            email="ana@test.com",
            is_buyer=True,
        )

        self.stdout.write(self.style.SUCCESS('Creating users...'))

        admin = User.objects.create_user(
            username='admin',
            password='admin123',
            role='admin'
        )

        agent1 = User.objects.create_user(
            username='carlos',
            password='test123',
            role='agent'
        )

        agent2 = User.objects.create_user(
            username='marta',
            password='test123',
            role='agent'
        )

        self.stdout.write(self.style.SUCCESS('Assigning properties...'))

        c1.properties.add(p1)
        c2.properties.add(p1, p2)
        c3.properties.add(p3)
        c4.properties.add(p2, p4)

        self.stdout.write(self.style.SUCCESS('Creating tasks...'))

        now = timezone.now()

        Task.objects.create(
            title="Llamar a Juan para seguimiento",
            description="Contactar para confirmar interés en el piso de Madrid",
            contact=c1,
            property=p1,
            assigned_to=agent1,
            created_by=admin,
            status="pending",
            priority="high",
            due_date=now + timedelta(days=1)
        )

        Task.objects.create(
            title="Agendar visita con Laura",
            description="Coordinar visita al ático en Valencia",
            contact=c2,
            property=p2,
            assigned_to=agent2,
            created_by=admin,
            status="in_progress",
            priority="medium",
            due_date=now + timedelta(days=2)
        )

        Task.objects.create(
            title="Negociación Pedro",
            description="Revisar oferta del chalet",
            contact=c3,
            property=p3,
            assigned_to=agent1,
            created_by=admin,
            status="pending",
            priority="high",
            due_date=now + timedelta(days=3)
        )

        Task.objects.create(
            title="Primer contacto Ana",
            description="Llamar para presentar propiedades disponibles",
            contact=c4,
            assigned_to=agent2,
            created_by=admin,
            status="done",
            priority="low",
            due_date=now + timedelta(days=5)
        )

        self.stdout.write(
            self.style.SUCCESS('Database seeded successfully!')
        )
