from django.core.management.base import BaseCommand

from contacts.models import Contact
from properties.models import Property


class Command(BaseCommand):

    help = 'Populate database with demo data'

    def handle(self, *args, **kwargs):

        self.stdout.write(self.style.WARNING('Deleting old data...'))

        Contact.objects.all().delete()
        Property.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('Creating properties...'))

        p1 = Property.objects.create(
            title="Piso en Madrid Centro",
            address="Gran Vía 123",
            city="Madrid",
            price=350000,
            property_type="flat"
        )

        p2 = Property.objects.create(
            title="Ático en Valencia",
            address="Calle Colón 45",
            city="Valencia",
            price=420000,
            property_type="flat"
        )

        p3 = Property.objects.create(
            title="Chalet en Sevilla",
            address="Avenida Sur 77",
            city="Sevilla",
            price=780000,
            property_type="villa"
        )

        p4 = Property.objects.create(
            title="Oficina en Barcelona",
            address="Diagonal 100",
            city="Barcelona",
            price=610000,
            property_type="office"
        )

        self.stdout.write(self.style.SUCCESS('Creating contacts...'))

        c1 = Contact.objects.create(
            name="Juan Pérez",
            phone="600111222",
            email="juan@test.com",
            status="interested"
        )

        c2 = Contact.objects.create(
            name="Laura Gómez",
            phone="611333444",
            email="laura@test.com",
            status="visit"
        )

        c3 = Contact.objects.create(
            name="Pedro Ruiz",
            phone="699888777",
            email="pedro@test.com",
            status="negotiation"
        )

        c4 = Contact.objects.create(
            name="Ana Torres",
            phone="644222111",
            email="ana@test.com",
            status="new"
        )

        self.stdout.write(self.style.SUCCESS('Assigning properties...'))

        c1.properties.add(p1)

        c2.properties.add(p1, p2)

        c3.properties.add(p3)

        c4.properties.add(p2, p4)

        self.stdout.write(
            self.style.SUCCESS('Database seeded successfully!')
        )