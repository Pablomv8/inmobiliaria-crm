from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from calendar_app.models import Appointment, Call, ProposalAppointment
from contacts.models import Contact
from listings.models import Listing
from news.models import News, NewsComment
from orders.models import Order, OrderComment
from properties.models import Property, PropertyComment
from tasks.models import Task

from .alerts import build_alerts, summarize_alerts


class AlertCenterTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.agent = User.objects.create_user(
            username="alert-agent",
            password="test-password",
            role="agent",
        )
        self.other_agent = User.objects.create_user(
            username="alert-other",
            password="test-password",
            role="agent",
        )
        self.manager = User.objects.create_user(
            username="alert-manager",
            password="test-password",
            role="manager",
        )
        self.owner = Contact.objects.create(
            name="Propietaria avisos",
            last_name="CRM",
            identification_number="12345678Z",
            phone="600100100",
            marital_status="single",
            is_owner=True,
            assigned_agent=self.agent,
        )
        self.buyer = Contact.objects.create(
            name="Comprador avisos",
            last_name="CRM",
            identification_number="12345679S",
            phone="600100101",
            marital_status="single",
            is_buyer=True,
            assigned_agent=self.agent,
        )
        self.property = Property.objects.create(
            street="Calle Avisos",
            number="1",
            city="Arcos de la Frontera",
            property_type="house",
            created_by=self.agent,
            assigned_agent=self.agent,
        )
        self.other_property = Property.objects.create(
            street="Calle Otros Avisos",
            number="2",
            city="Arcos de la Frontera",
            property_type="house",
            created_by=self.other_agent,
            assigned_agent=self.other_agent,
        )

    def test_agents_only_receive_their_alerts_and_manager_sees_the_office(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        own_task = Task.objects.create(
            task_type="custom",
            title="Tarea propia vencida",
            description="Pendiente propia",
            assigned_to=self.agent,
            created_by=self.manager,
            due_date=timezone.now() - timedelta(days=1),
        )
        other_task = Task.objects.create(
            task_type="custom",
            title="Tarea ajena vencida",
            description="Pendiente ajena",
            assigned_to=self.other_agent,
            created_by=self.manager,
            due_date=timezone.now() - timedelta(days=1),
        )
        own_appointment = Appointment.objects.create(
            related_property=self.property,
            contact=self.owner,
            agent=self.agent,
            appointment_type="valuation",
            date=yesterday,
            time=time(10, 0),
            end_time=time(11, 0),
        )
        other_appointment = Appointment.objects.create(
            related_property=self.other_property,
            contact=self.owner,
            agent=self.other_agent,
            appointment_type="valuation",
            date=yesterday,
            time=time(12, 0),
            end_time=time(13, 0),
        )

        agent_keys = {item.key for item in build_alerts(self.agent)}
        manager_keys = {item.key for item in build_alerts(self.manager)}

        self.assertIn(f"task-{own_task.pk}", agent_keys)
        self.assertIn(f"appointment-{own_appointment.pk}", agent_keys)
        self.assertNotIn(f"task-{other_task.pk}", agent_keys)
        self.assertNotIn(f"appointment-{other_appointment.pk}", agent_keys)
        self.assertIn(f"task-{own_task.pk}", manager_keys)
        self.assertIn(f"task-{other_task.pk}", manager_keys)
        self.assertIn(f"appointment-{other_appointment.pk}", manager_keys)

    def test_center_detects_expirations_inactivity_and_workflow_decisions(self):
        today = timezone.localdate()
        stale_at = timezone.now() - timedelta(days=35)
        Property.objects.filter(pk=self.property.pk).update(created_at=stale_at)

        listing = Listing.objects.create(
            property=self.property,
            listing_type="sale",
            owner_price="190000",
            agency_price="195000",
            agreed_price="193000",
            price_diference="5000",
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=2),
            owner=self.owner,
            agent=self.agent,
        )
        order = Order.objects.create(
            buyer=self.buyer,
            agent=self.agent,
            operation_type="sale",
            max_price="210000",
            payment_type="financing",
            property_type="house",
        )
        source_appointment = Appointment.objects.create(
            related_property=self.property,
            contact=self.buyer,
            agent=self.agent,
            appointment_type="proposal",
            date=today - timedelta(days=1),
            time=time(10, 0),
            end_time=time(11, 0),
            status="completed",
            result_comment="Oferta acordada.",
            listing=listing,
            order=order,
        )
        proposal = ProposalAppointment.objects.create(
            source_sale_appointment=source_appointment,
            order=order,
            listing=listing,
            buyer=self.buyer,
            agent=self.agent,
            listing_price="193000",
            offered_price="187000",
            deposit_amount="5000",
            proposal_date=today,
            end_date=today + timedelta(days=1),
        )
        acquisition = Appointment.objects.create(
            related_property=self.property,
            contact=self.owner,
            agent=self.agent,
            appointment_type="acquisition",
            date=today - timedelta(days=1),
            time=time(12, 0),
            end_time=time(13, 0),
            status="completed",
            result_comment="Reunión terminada.",
        )
        stale_news = News.objects.create(
            related_property=self.other_property,
            agent=self.agent,
            motivation="sale",
            client_price="180000",
            estimated_price="185000",
        )
        News.objects.filter(pk=stale_news.pk).update(created_at=stale_at)
        stale_order = Order.objects.create(
            buyer=self.buyer,
            agent=self.agent,
            operation_type="sale",
            max_price="220000",
            payment_type="cash",
            property_type="house",
        )
        Order.objects.filter(pk=stale_order.pk).update(
            created_at=stale_at,
            updated_at=stale_at,
        )

        alerts = build_alerts(self.agent)
        keys = {item.key for item in alerts}

        self.assertIn(f"listing-expiration-{listing.pk}", keys)
        self.assertIn(f"proposal-expiration-{proposal.pk}", keys)
        self.assertIn(f"workflow-appointment-{acquisition.pk}", keys)
        self.assertIn(f"news-inactivity-{stale_news.pk}", keys)
        self.assertIn(f"order-inactivity-{stale_order.pk}", keys)
        summary = summarize_alerts(alerts)
        self.assertGreaterEqual(summary["high"], 1)
        self.assertGreaterEqual(summary["categories"]["expirations"], 2)

    def test_recent_comments_remove_inactivity_alerts(self):
        stale_at = timezone.now() - timedelta(days=35)
        Property.objects.filter(pk=self.property.pk).update(created_at=stale_at)
        PropertyComment.objects.create(
            property=self.property,
            user=self.agent,
            text="Contacto realizado hoy.",
        )
        news_item = News.objects.create(
            related_property=self.other_property,
            agent=self.agent,
            motivation="sale",
            client_price="180000",
            estimated_price="185000",
        )
        News.objects.filter(pk=news_item.pk).update(created_at=stale_at)
        NewsComment.objects.create(
            news=news_item,
            user=self.agent,
            text="Seguimiento reciente.",
        )
        order = Order.objects.create(
            buyer=self.buyer,
            agent=self.agent,
            operation_type="sale",
            max_price="220000",
            payment_type="cash",
            property_type="house",
        )
        Order.objects.filter(pk=order.pk).update(
            created_at=stale_at,
            updated_at=stale_at,
        )
        OrderComment.objects.create(
            order=order,
            user=self.agent,
            text="Pedido revisado hoy.",
        )

        keys = {item.key for item in build_alerts(self.agent)}

        self.assertNotIn(f"property-inactivity-{self.property.pk}", keys)
        self.assertNotIn(f"news-inactivity-{news_item.pk}", keys)
        self.assertNotIn(f"order-inactivity-{order.pk}", keys)

    def test_center_renders_filters_badge_and_direct_links(self):
        task = Task.objects.create(
            task_type="custom",
            title="Revisar documentación vencida",
            description="Avisar al cliente",
            assigned_to=self.agent,
            created_by=self.manager,
            due_date=timezone.now() - timedelta(days=1),
        )
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("alert_center"),
            {"priority": "high", "category": "tasks", "search": "documentación"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Avisos y pendientes críticos")
        self.assertContains(response, "Revisar documentación vencida")
        self.assertContains(response, reverse("task_detail", args=[task.pk]))
        self.assertContains(response, "Avisos")
        self.assertEqual(len(response.context["alerts"]), 1)

    def test_manager_can_filter_the_center_by_agent(self):
        Task.objects.create(
            task_type="custom",
            title="Pendiente agente uno",
            description="Aviso",
            assigned_to=self.agent,
            created_by=self.manager,
            due_date=timezone.now() - timedelta(days=1),
        )
        Task.objects.create(
            task_type="custom",
            title="Pendiente agente dos",
            description="Aviso",
            assigned_to=self.other_agent,
            created_by=self.manager,
            due_date=timezone.now() - timedelta(days=1),
        )
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("alert_center"),
            {"category": "tasks", "agent": self.other_agent.pk},
        )

        titles = [item.title + item.description for item in response.context["alerts"]]
        self.assertEqual(len(titles), 1)
        self.assertIn("Pendiente agente dos", titles[0])
