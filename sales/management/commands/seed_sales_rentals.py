from datetime import time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from calendar_app.models import Appointment
from contacts.models import Contact
from listings.models import Listing
from orders.models import Order
from properties.models import Property, Zone
from sales.models import RentalContract, Sale
from users.models import User


class Command(BaseCommand):
    help = "Crea ventas y alquileres de demostración de forma idempotente"

    username = "demo_operaciones"
    password = "DemoCRM2026!"
    marker = "[DEMO OPERACIONES]"

    sales_data = (
        {
            "reference": "CV-DEMO-001",
            "street": "Demo Venta Gran Vía",
            "number": "18",
            "property_type": "flat",
            "owner": ("DEMO-V-OWNER-01", "Carmen", "Santos"),
            "client": ("DEMO-V-BUYER-01", "Laura", "Romero"),
            "price": "315000.00",
            "listing_price": "325000.00",
            "deposit": "10000.00",
            "earnest": "20000.00",
            "seller_commission": "9450.00",
            "buyer_commission": "2500.00",
            "days_ago": 12,
            "status": "signed",
        },
        {
            "reference": "CV-DEMO-002",
            "street": "Demo Venta Nave Industrial",
            "number": "42",
            "property_type": "nave",
            "owner": ("DEMO-V-OWNER-02", "Miguel", "Herrera"),
            "client": ("DEMO-V-BUYER-02", "Inversiones", "Alameda"),
            "price": "540000.00",
            "listing_price": "565000.00",
            "deposit": "25000.00",
            "earnest": "40000.00",
            "seller_commission": "16200.00",
            "buyer_commission": "5000.00",
            "days_ago": 35,
            "status": "signed",
        },
        {
            "reference": "CV-DEMO-003",
            "street": "Demo Venta Local Centro",
            "number": "7",
            "property_type": "local",
            "owner": ("DEMO-V-OWNER-03", "Teresa", "Navarro"),
            "client": ("DEMO-V-BUYER-03", "Daniel", "Martín"),
            "price": "185000.00",
            "listing_price": "195000.00",
            "deposit": "5000.00",
            "earnest": "0.00",
            "seller_commission": "5550.00",
            "buyer_commission": "0.00",
            "days_ago": 5,
            "status": "cancelled",
        },
        {
            "reference": "CV-DEMO-004",
            "street": "Demo Venta Villa Encinar",
            "number": "3",
            "property_type": "villa",
            "owner": ("DEMO-V-OWNER-04", "Andrés", "Molina"),
            "client": ("DEMO-V-BUYER-04", "Patricia", "Gil"),
            "price": "725000.00",
            "listing_price": "750000.00",
            "deposit": "30000.00",
            "earnest": "50000.00",
            "seller_commission": "21750.00",
            "buyer_commission": "7500.00",
            "days_ago": 2,
            "status": "draft",
        },
    )

    rentals_data = (
        {
            "reference": "ALQ-DEMO-001",
            "street": "Demo Alquiler Chamberí",
            "number": "21",
            "property_type": "flat",
            "owner": ("DEMO-A-OWNER-01", "Isabel", "Vega"),
            "client": ("DEMO-A-TENANT-01", "Álvaro", "Ruiz"),
            "rent": "1350.00",
            "deposit": "2700.00",
            "earnest": "0.00",
            "owner_commission": "1350.00",
            "tenant_commission": "675.00",
            "days_ago": 8,
            "duration_days": 365,
            "status": "signed",
        },
        {
            "reference": "ALQ-DEMO-002",
            "street": "Demo Alquiler Local Mercado",
            "number": "15",
            "property_type": "local",
            "owner": ("DEMO-A-OWNER-02", "Ramón", "Pastor"),
            "client": ("DEMO-A-TENANT-02", "Panadería", "Rosales"),
            "rent": "2200.00",
            "deposit": "4400.00",
            "earnest": "2200.00",
            "owner_commission": "2200.00",
            "tenant_commission": "1100.00",
            "days_ago": 24,
            "duration_days": 730,
            "status": "signed",
        },
        {
            "reference": "ALQ-DEMO-003",
            "street": "Demo Alquiler Nave Logística",
            "number": "63",
            "property_type": "nave",
            "owner": ("DEMO-A-OWNER-03", "Beatriz", "Ortega"),
            "client": ("DEMO-A-TENANT-03", "Logística", "Norte"),
            "rent": "3900.00",
            "deposit": "7800.00",
            "earnest": "3900.00",
            "owner_commission": "3900.00",
            "tenant_commission": "1950.00",
            "days_ago": 42,
            "duration_days": 1095,
            "status": "signed",
        },
        {
            "reference": "ALQ-DEMO-004",
            "street": "Demo Alquiler Oficina Castellana",
            "number": "108",
            "property_type": "office",
            "owner": ("DEMO-A-OWNER-04", "Jorge", "Blanco"),
            "client": ("DEMO-A-TENANT-04", "Consultoría", "Delta"),
            "rent": "1600.00",
            "deposit": "3200.00",
            "earnest": "0.00",
            "owner_commission": "1600.00",
            "tenant_commission": "800.00",
            "days_ago": 3,
            "duration_days": 365,
            "status": "cancelled",
        },
    )

    @transaction.atomic
    def handle(self, *args, **options):
        agent = self.create_agent()
        zone, _ = Zone.objects.update_or_create(
            name="Zona Demo Operaciones",
            defaults={
                "description": "Inmuebles de prueba para los apartados de ventas y alquileres.",
            },
        )

        for index, data in enumerate(self.sales_data):
            self.create_sale(data, agent, zone, index)
        for index, data in enumerate(self.rentals_data):
            self.create_rental(data, agent, zone, index)

        self.stdout.write(self.style.SUCCESS("Datos de ventas y alquileres preparados."))
        self.stdout.write(f"Usuario: {self.username}")
        self.stdout.write(f"Contraseña: {self.password}")
        self.stdout.write(
            f"Ventas demo: {Sale.objects.filter(contract_reference__startswith='CV-DEMO-').count()}"
        )
        self.stdout.write(
            "Alquileres demo: "
            f"{RentalContract.objects.filter(contract_reference__startswith='ALQ-DEMO-').count()}"
        )

    def create_agent(self):
        agent, _ = User.objects.get_or_create(username=self.username)
        agent.first_name = "Agente"
        agent.last_name = "Operaciones Demo"
        agent.email = "operaciones.demo@example.com"
        agent.role = "agent"
        agent.set_password(self.password)
        agent.save()
        return agent

    def create_contact(self, identity, name, last_name, contact_type, agent):
        contact = Contact.objects.filter(identification_number=identity).first()
        values = {
            "name": name,
            "last_name": last_name,
            "phone": f"610 8{identity[-2:]} 000",
            "email": f"{identity.lower()}@example.com",
            "contact_type": contact_type,
            "assigned_agent": agent,
            "notes": f"{self.marker} Contacto para operaciones cerradas.",
        }
        if contact is None:
            return Contact.objects.create(
                identification_number=identity,
                **values,
            )
        for field, value in values.items():
            setattr(contact, field, value)
        contact.save()
        return contact

    def create_property(self, data, zone):
        property_obj, _ = Property.objects.update_or_create(
            street=data["street"],
            number=data["number"],
            city="Madrid",
            defaults={
                "province": "Madrid",
                "postal_code": "28080",
                "property_type": data["property_type"],
                "zone": zone,
                "description": f"{self.marker} {data['reference']}",
                "occupied_by": "owner",
            },
        )
        return property_obj

    def create_listing(self, data, property_obj, owner, agent, operation_type):
        price = Decimal(data.get("listing_price", data.get("rent")))
        closed_status = (
            "sold"
            if operation_type == "sale" and data["status"] == "signed"
            else "rented"
            if operation_type == "rent" and data["status"] == "signed"
            else "cancelled"
            if data["status"] == "cancelled"
            else "active"
        )
        listing, _ = Listing.objects.update_or_create(
            property=property_obj,
            listing_type=operation_type,
            defaults={
                "status": closed_status,
                "workflow_status": "closed" if closed_status in ("sold", "rented") else "active",
                "owner_price": price,
                "agency_price": price,
                "agreed_price": price,
                "price_diference": Decimal("0.00"),
                "is_exclusive": True,
                "start_date": timezone.localdate() - timedelta(days=data["days_ago"] + 60),
                "end_date": timezone.localdate() + timedelta(days=90),
                "commission_amount": Decimal(
                    data.get("seller_commission", data.get("owner_commission", "0"))
                ),
                "owner": owner,
                "agent": agent,
            },
        )
        return listing

    def create_order(self, data, client, zone, operation_type, agent):
        order, _ = Order.objects.update_or_create(
            buyer=client,
            operation_type=operation_type,
            notes=f"{self.marker} Pedido de {data['reference']}",
            defaults={
                "agent": agent,
                "status": "closed",
                "zone": zone,
                "max_price": Decimal(data.get("listing_price", data.get("rent"))),
                "payment_type": "financing" if operation_type == "sale" else "cash",
                "property_type": data["property_type"],
                "bedrooms": 2 if data["property_type"] in ("flat", "house", "villa") else None,
                "bathrooms": 1,
            },
        )
        return order

    def create_contract_appointment(self, data, property_obj, client, listing, order, agent, index):
        appointment, _ = Appointment.objects.update_or_create(
            agent=agent,
            notes=f"{self.marker} Contrato {data['reference']}",
            defaults={
                "related_property": property_obj,
                "contact": client,
                "appointment_type": "contract",
                "date": timezone.localdate() - timedelta(days=data["days_ago"]),
                "time": time(9 + index, 0),
                "end_time": time(10 + index, 0),
                "result_comment": "Contrato revisado con las partes para probar el cierre.",
                "result_success": data["status"] == "signed",
                "status": "completed",
                "listing": listing,
                "order": order,
            },
        )
        return appointment

    def create_sale(self, data, agent, zone, index):
        owner = self.create_contact(*data["owner"], "owner", agent)
        buyer = self.create_contact(*data["client"], "buyer", agent)
        property_obj = self.create_property(data, zone)
        property_obj.contacts.add(owner)
        listing = self.create_listing(data, property_obj, owner, agent, "sale")
        order = self.create_order(data, buyer, zone, "sale", agent)
        appointment = self.create_contract_appointment(
            data, property_obj, buyer, listing, order, agent, index
        )
        seller_commission = Decimal(data["seller_commission"])
        buyer_commission = Decimal(data["buyer_commission"])
        sale, _ = Sale.objects.update_or_create(
            contract_reference=data["reference"],
            defaults={
                "related_property": property_obj,
                "buyer": buyer,
                "agent": agent,
                "sale_price": Decimal(data["price"]),
                "commission_amount": seller_commission + buyer_commission,
                "seller_commission": seller_commission,
                "buyer_commission": buyer_commission,
                "deposit_amount": Decimal(data["deposit"]),
                "earnest_money_amount": Decimal(data["earnest"]),
                "sale_date": timezone.localdate() - timedelta(days=data["days_ago"]),
                "listing": listing,
                "order": order,
                "source_contract_appointment": appointment,
                "former_owner": owner,
                "status": data["status"],
                "notes": f"{self.marker} Compraventa para probar listados y detalles.",
            },
        )
        if data["status"] == "signed":
            property_obj.contacts.remove(owner)
            property_obj.contacts.add(buyer)
            buyer.contact_type = "owner"
            buyer.save(update_fields=["contact_type"])
            property_obj.occupied_by = "owner"
        property_obj.save()
        return sale

    def create_rental(self, data, agent, zone, index):
        owner = self.create_contact(*data["owner"], "owner", agent)
        tenant = self.create_contact(*data["client"], "buyer", agent)
        property_obj = self.create_property(data, zone)
        property_obj.contacts.add(owner, tenant)
        listing = self.create_listing(data, property_obj, owner, agent, "rent")
        order = self.create_order(data, tenant, zone, "rent", agent)
        appointment = self.create_contract_appointment(
            data, property_obj, tenant, listing, order, agent, index
        )
        contract_date = timezone.localdate() - timedelta(days=data["days_ago"])
        contract, _ = RentalContract.objects.update_or_create(
            contract_reference=data["reference"],
            defaults={
                "related_property": property_obj,
                "listing": listing,
                "order": order,
                "tenant": tenant,
                "owner": owner,
                "agent": agent,
                "source_contract_appointment": appointment,
                "rent_price": Decimal(data["rent"]),
                "deposit_amount": Decimal(data["deposit"]),
                "owner_commission": Decimal(data["owner_commission"]),
                "tenant_commission": Decimal(data["tenant_commission"]),
                "earnest_money_amount": Decimal(data["earnest"]),
                "contract_date": contract_date,
                "start_date": contract_date,
                "end_date": contract_date + timedelta(days=data["duration_days"]),
                "status": data["status"],
                "notes": f"{self.marker} Alquiler para probar listados y detalles.",
            },
        )
        property_obj.occupied_by = "tenants" if data["status"] == "signed" else "owner"
        property_obj.save()
        return contract
