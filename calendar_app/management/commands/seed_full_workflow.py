from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from calendar_app.models import Appointment, Call, ProposalAppointment
from contacts.models import Contact
from listings.models import Listing, ListingComment
from news.models import News, NewsComment
from orders.models import Order, OrderComment
from properties.models import Property, Zone
from users.models import User


class Command(BaseCommand):
    help = "Crea datos idempotentes para probar todas las fases del flujo comercial"

    username = "demo_flujo_integral"
    password = "DemoCRM2026!"
    marker = "[DEMO FLUJO INTEGRAL]"

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()
        agent = self.create_agent()
        zone, _ = Zone.objects.update_or_create(
            name="Zona Demo Integral",
            defaults={
                "description": "Zona aislada para probar el flujo comercial completo.",
            },
        )
        owner = self.create_contact(
            identification_number="DEMO-INTEGRAL-OWNER",
            name="Elena",
            last_name="Propietaria Integral",
            phone="610 000 101",
            email="elena.integral@example.com",
            contact_type="owner",
            assigned_agent=agent,
            notes="Propietaria para los escenarios integrales de prueba.",
        )
        buyer = self.create_contact(
            identification_number="DEMO-INTEGRAL-BUYER",
            name="Javier",
            last_name="Comprador Integral",
            phone="610 000 202",
            email="javier.integral@example.com",
            contact_type="buyer",
            assigned_agent=agent,
            notes="Comprador para los escenarios integrales de prueba.",
        )

        property_news = self.create_property(
            zone=zone,
            street="Demo Flujo Noticia",
            number="1",
            property_type="local",
            status="prospect",
        )
        property_pending = self.create_property(
            zone=zone,
            street="Demo Flujo Adquisición",
            number="2",
            property_type="solar",
            status="prospect",
        )
        property_decision = self.create_property(
            zone=zone,
            street="Demo Flujo Decisión",
            number="3",
            property_type="terreno",
            status="prospect",
        )
        property_unsuccessful = self.create_property(
            zone=zone,
            street="Demo Flujo Sin Encargo",
            number="4",
            property_type="office",
            status="prospect",
        )
        property_listing = self.create_property(
            zone=zone,
            street="Demo Flujo Comercial",
            number="5",
            property_type="flat",
            status="active",
            bedrooms=3,
            bathrooms=2,
            area=105,
            built_area=118,
        )
        owner.properties.add(
            property_news,
            property_pending,
            property_decision,
            property_unsuccessful,
            property_listing,
        )

        news_initial = self.create_news(
            property_news,
            agent,
            "195000.00",
            "185000.00",
            "new",
        )
        news_pending = self.create_news(
            property_pending,
            agent,
            "150000.00",
            "142000.00",
            "appointment",
        )
        news_decision = self.create_news(
            property_decision,
            agent,
            "285000.00",
            "270000.00",
            "appointment",
        )
        news_unsuccessful = self.create_news(
            property_unsuccessful,
            agent,
            "230000.00",
            "215000.00",
            "follow_up",
        )
        news_success = self.create_news(
            property_listing,
            agent,
            "300000.00",
            "290000.00",
            "closed",
        )
        NewsComment.objects.get_or_create(
            news=news_pending,
            text=f"{self.marker} El propietario acepta una primera reunión.",
            defaults={"user": agent},
        )
        NewsComment.objects.get_or_create(
            news=news_success,
            text=f"{self.marker} Condiciones iniciales documentadas.",
            defaults={"user": agent},
        )

        acquisition_pending = self.create_appointment(
            marker="Adquisición pendiente de comentario",
            related_property=property_pending,
            contact=owner,
            agent=agent,
            appointment_type="acquisition",
            appointment_date=today + timedelta(days=1),
            appointment_time=time(9, 0),
            status="scheduled",
            news=news_pending,
        )
        acquisition_decision = self.create_appointment(
            marker="Adquisición pendiente de decidir",
            related_property=property_decision,
            contact=owner,
            agent=agent,
            appointment_type="acquisition",
            appointment_date=today,
            appointment_time=time(10, 0),
            status="completed",
            result_comment="El propietario está interesado; falta decidir el siguiente paso.",
            news=news_decision,
        )
        acquisition_no = self.create_appointment(
            marker="Adquisición sin éxito",
            related_property=property_unsuccessful,
            contact=owner,
            agent=agent,
            appointment_type="acquisition",
            appointment_date=today - timedelta(days=2),
            appointment_time=time(10, 30),
            status="completed",
            result_comment="El propietario todavía no desea firmar un encargo.",
            result_success=False,
            news=news_unsuccessful,
        )
        acquisition_success = self.create_appointment(
            marker="Adquisición con encargo",
            related_property=property_listing,
            contact=owner,
            agent=agent,
            appointment_type="acquisition",
            appointment_date=today - timedelta(days=30),
            appointment_time=time(11, 0),
            status="completed",
            result_comment="Se acuerda comercializar el inmueble en exclusiva.",
            result_success=True,
            news=news_success,
        )
        self.create_call(
            marker="Llamada tras adquisición sin éxito",
            contact=owner,
            agent=agent,
            call_date=today + timedelta(days=2),
            call_time=time(12, 0),
            status="pending",
            news=news_unsuccessful,
        )

        listing, _ = Listing.objects.update_or_create(
            property=property_listing,
            listing_type="sale",
            defaults={
                "status": "active",
                "owner_price": "285000.00",
                "agency_price": "300000.00",
                "agreed_price": "295000.00",
                "price_diference": "15000.00",
                "is_exclusive": True,
                "start_date": today - timedelta(days=29),
                "end_date": today + timedelta(days=150),
                "commission_amount": "10500.00",
                "owner": owner,
                "source_appointment": acquisition_success,
                "agent": agent,
            },
        )
        ListingComment.objects.get_or_create(
            listing=listing,
            text=f"{self.marker} Se publica el inmueble en los portales principales.",
            defaults={"user": agent},
        )
        ListingComment.objects.get_or_create(
            listing=listing,
            text=f"{self.marker} El propietario confirma que mantiene el precio.",
            defaults={"user": agent},
        )
        self.create_appointment(
            marker="Seguimiento programado",
            related_property=property_listing,
            contact=owner,
            agent=agent,
            appointment_type="follow_up",
            appointment_date=today + timedelta(days=3),
            appointment_time=time(9, 30),
            status="scheduled",
            listing=listing,
        )
        self.create_appointment(
            marker="Seguimiento completado",
            related_property=property_listing,
            contact=owner,
            agent=agent,
            appointment_type="follow_up",
            appointment_date=today - timedelta(days=7),
            appointment_time=time(9, 30),
            status="completed",
            result_comment="Se revisan las visitas y el propietario mantiene el encargo activo.",
            listing=listing,
        )
        self.create_appointment(
            marker="Seguimiento cancelado",
            related_property=property_listing,
            contact=owner,
            agent=agent,
            appointment_type="follow_up",
            appointment_date=today - timedelta(days=1),
            appointment_time=time(9, 30),
            status="cancelled",
            listing=listing,
        )
        self.create_call(
            marker="Llamada de seguimiento del encargo",
            contact=owner,
            agent=agent,
            call_date=today + timedelta(days=4),
            call_time=time(10, 30),
            status="pending",
            listing=listing,
        )

        order, _ = Order.objects.update_or_create(
            buyer=buyer,
            property_type="flat",
            defaults={
                "agent": agent,
                "operation_type": "sale",
                "zone": zone,
                "max_price": "325000.00",
                "payment_type": "financing",
                "bedrooms": 3,
                "bathrooms": 2,
                "notes": "Busca terraza, ascensor y buena conexión con transporte público.",
            },
        )
        OrderComment.objects.get_or_create(
            order=order,
            text=f"{self.marker} Tiene financiación preconcedida al 80 %.",
            defaults={"user": agent},
        )
        OrderComment.objects.get_or_create(
            order=order,
            text=f"{self.marker} Puede visitar inmuebles por las tardes.",
            defaults={"user": agent},
        )

        sale_scheduled = self.create_sale_appointment(
            "Venta programada",
            listing,
            order,
            buyer,
            agent,
            today + timedelta(days=5),
            time(17, 0),
            "scheduled",
        )
        sale_decision = self.create_sale_appointment(
            "Venta pendiente de decidir",
            listing,
            order,
            buyer,
            agent,
            today - timedelta(days=1),
            time(17, 0),
            "completed",
            result_comment="La visita ha finalizado y el comprador está valorando el inmueble.",
        )
        self.create_sale_appointment(
            "Venta sin propuesta",
            listing,
            order,
            buyer,
            agent,
            today - timedelta(days=6),
            time(17, 30),
            "completed",
            result_comment="La distribución no se ajusta a sus necesidades.",
            result_success=False,
        )
        sale_proposal_scheduled = self.create_sale_appointment(
            "Venta con cita de propuesta programada",
            listing,
            order,
            buyer,
            agent,
            today - timedelta(days=5),
            time(18, 0),
            "completed",
            result_comment="El comprador quiere reunirse para preparar una oferta.",
            result_success=True,
        )
        proposal_scheduled = self.create_proposal_appointment(
            "Propuesta programada",
            sale_proposal_scheduled,
            listing,
            order,
            buyer,
            agent,
            today + timedelta(days=6),
            time(18, 0),
            "scheduled",
        )

        sale_proposal_pending_offer = self.create_sale_appointment(
            "Venta con propuesta pendiente de registrar",
            listing,
            order,
            buyer,
            agent,
            today - timedelta(days=4),
            time(18, 30),
            "completed",
            result_comment="El comprador solicita una reunión para formalizar su oferta.",
            result_success=True,
        )
        proposal_pending_offer = self.create_proposal_appointment(
            "Propuesta completada sin oferta registrada",
            sale_proposal_pending_offer,
            listing,
            order,
            buyer,
            agent,
            today - timedelta(days=3),
            time(18, 30),
            "completed",
            result_comment="Se concretan precio, señal y plazo de validez.",
        )

        sale_with_offer = self.create_sale_appointment(
            "Venta con propuesta registrada",
            listing,
            order,
            buyer,
            agent,
            today - timedelta(days=12),
            time(16, 30),
            "completed",
            result_comment="El comprador confirma que presentará una oferta formal.",
            result_success=True,
        )
        proposal_completed = self.create_proposal_appointment(
            "Propuesta con oferta registrada",
            sale_with_offer,
            listing,
            order,
            buyer,
            agent,
            today - timedelta(days=11),
            time(16, 30),
            "completed",
            result_comment="El comprador firma y entrega la señal acordada.",
        )
        purchase_proposal, _ = ProposalAppointment.objects.update_or_create(
            source_sale_appointment=proposal_completed,
            defaults={
                "order": order,
                "listing": listing,
                "buyer": buyer,
                "agent": agent,
                "listing_price": listing.agreed_price,
                "offered_price": "292000.00",
                "deposit_amount": "6000.00",
                "proposal_date": today - timedelta(days=11),
                "end_date": today + timedelta(days=3),
            },
        )

        self.print_summary(
            news_initial=news_initial,
            acquisition_pending=acquisition_pending,
            acquisition_decision=acquisition_decision,
            acquisition_no=acquisition_no,
            listing=listing,
            order=order,
            sale_scheduled=sale_scheduled,
            sale_decision=sale_decision,
            proposal_scheduled=proposal_scheduled,
            proposal_pending_offer=proposal_pending_offer,
            purchase_proposal=purchase_proposal,
        )

    def create_agent(self):
        agent, _ = User.objects.get_or_create(username=self.username)
        agent.first_name = "Agente"
        agent.last_name = "Flujo Integral"
        agent.email = "demo.integral@example.com"
        agent.role = "agent"
        agent.set_password(self.password)
        agent.save()
        return agent

    def create_contact(self, identification_number, **defaults):
        contact = Contact.objects.filter(
            identification_number=identification_number
        ).first()
        if contact is None:
            return Contact.objects.create(
                identification_number=identification_number,
                **defaults,
            )
        for field, value in defaults.items():
            setattr(contact, field, value)
        contact.save()
        return contact

    def create_property(self, zone, street, number, property_type, status, **extra):
        property_obj, _ = Property.objects.update_or_create(
            street=street,
            number=number,
            city="Madrid",
            defaults={
                "province": "Madrid",
                "postal_code": "28080",
                "property_type": property_type,
                "zone": zone,
                "status": status,
                "description": "Inmueble aislado para probar el flujo integral.",
                **extra,
            },
        )
        return property_obj

    def create_news(self, property_obj, agent, client_price, estimated_price, status):
        news, _ = News.objects.update_or_create(
            related_property=property_obj,
            motivation="sale",
            defaults={
                "agent": agent,
                "client_price": client_price,
                "estimated_price": estimated_price,
                "status": status,
            },
        )
        return news

    def create_appointment(
        self,
        marker,
        related_property,
        contact,
        agent,
        appointment_type,
        appointment_date,
        appointment_time,
        status,
        result_comment="",
        result_success=None,
        news=None,
        listing=None,
        order=None,
        source_sale_appointment=None,
    ):
        notes = f"{self.marker} {marker}"
        appointment = Appointment.objects.filter(agent=agent, notes=notes).first()
        values = {
            "related_property": related_property,
            "contact": contact,
            "agent": agent,
            "appointment_type": appointment_type,
            "date": appointment_date,
            "time": appointment_time,
            "end_time": time(
                *divmod(
                    min(
                        appointment_time.hour * 60
                        + appointment_time.minute
                        + 60,
                        23 * 60 + 59,
                    ),
                    60,
                )
            ),
            "notes": notes,
            "status": status,
            "result_comment": result_comment,
            "result_success": result_success,
            "news": news,
            "listing": listing,
            "order": order,
            "source_sale_appointment": source_sale_appointment,
        }
        if appointment is None:
            appointment = Appointment.objects.create(**values)
        else:
            for field, value in values.items():
                setattr(appointment, field, value)
            appointment.save()
        return appointment

    def create_sale_appointment(
        self,
        marker,
        listing,
        order,
        buyer,
        agent,
        appointment_date,
        appointment_time,
        status,
        result_comment="",
        result_success=None,
    ):
        return self.create_appointment(
            marker=marker,
            related_property=listing.property,
            contact=buyer,
            agent=agent,
            appointment_type="sale",
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status=status,
            result_comment=result_comment,
            result_success=result_success,
            listing=listing,
            order=order,
        )

    def create_proposal_appointment(
        self,
        marker,
        sale_appointment,
        listing,
        order,
        buyer,
        agent,
        appointment_date,
        appointment_time,
        status,
        result_comment="",
    ):
        return self.create_appointment(
            marker=marker,
            related_property=listing.property,
            contact=buyer,
            agent=agent,
            appointment_type="proposal",
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status=status,
            result_comment=result_comment,
            listing=listing,
            order=order,
            source_sale_appointment=sale_appointment,
        )

    def create_call(
        self,
        marker,
        contact,
        agent,
        call_date,
        call_time,
        status,
        news=None,
        listing=None,
    ):
        notes = f"{self.marker} {marker}"
        call = Call.objects.filter(agent=agent, notes=notes).first()
        values = {
            "contact": contact,
            "agent": agent,
            "date": call_date,
            "time": call_time,
            "notes": notes,
            "status": status,
            "news": news,
            "listing": listing,
        }
        if call is None:
            call = Call.objects.create(**values)
        else:
            for field, value in values.items():
                setattr(call, field, value)
            call.save()
        return call

    def print_summary(self, **objects):
        self.stdout.write(self.style.SUCCESS("Datos del flujo integral preparados."))
        self.stdout.write("")
        self.stdout.write(f"Usuario: {self.username}")
        self.stdout.write(f"Contraseña: {self.password}")
        self.stdout.write("")
        links = [
            ("Noticia sin cita", "news_detail", objects["news_initial"].pk),
            ("Adquisición pendiente de comentario", "appointment_detail", objects["acquisition_pending"].pk),
            ("Adquisición pendiente de decisión", "appointment_detail", objects["acquisition_decision"].pk),
            ("Adquisición sin encargo", "appointment_detail", objects["acquisition_no"].pk),
            ("Encargo con seguimientos", "listing_detail", objects["listing"].pk),
            ("Pedido con comentarios y visitas", "order_detail", objects["order"].pk),
            ("Cita de venta programada", "appointment_detail", objects["sale_scheduled"].pk),
            ("Cita de venta pendiente de decisión", "appointment_detail", objects["sale_decision"].pk),
            ("Cita de propuesta programada", "appointment_detail", objects["proposal_scheduled"].pk),
            ("Cita de propuesta lista para crear oferta", "appointment_detail", objects["proposal_pending_offer"].pk),
            ("Propuesta económica registrada", "proposal_appointment_detail", objects["purchase_proposal"].pk),
        ]
        for label, route, pk in links:
            self.stdout.write(f"- {label}: {reverse(route, args=[pk])}")
        self.stdout.write(f"- Calendario del agente: {reverse('calendar')}")
