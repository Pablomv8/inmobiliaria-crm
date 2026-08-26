from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from calendar_app.models import Appointment
from contacts.models import Contact
from news.models import News
from orders.models import Order
from properties.models import Property
from sales.models import Sale
from tasks.models import Task


class CrmObjectPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.agent = User.objects.create_user(
            username="security-agent",
            password="test-password",
            role="agent",
        )
        self.other_agent = User.objects.create_user(
            username="security-other-agent",
            password="test-password",
            role="agent",
        )
        self.manager = User.objects.create_user(
            username="security-manager",
            password="test-password",
            role="manager",
        )
        self.own_contact = Contact.objects.create(
            name="Contacto propio",
            phone="600000001",
            is_buyer=True,
            assigned_agent=self.agent,
        )
        self.other_contact = Contact.objects.create(
            name="Contacto ajeno",
            phone="600000002",
            is_buyer=True,
            assigned_agent=self.other_agent,
        )
        self.own_property = Property.objects.create(
            street="Calle propia",
            number="1",
            city="Madrid",
            property_type="flat",
            created_by=self.agent,
        )
        self.other_property = Property.objects.create(
            street="Calle ajena",
            number="2",
            city="Madrid",
            property_type="flat",
            created_by=self.other_agent,
        )
        self.own_news = News.objects.create(
            related_property=self.own_property,
            agent=self.agent,
            motivation="sale",
            client_price="200000",
            estimated_price="195000",
        )
        self.other_news = News.objects.create(
            related_property=self.other_property,
            agent=self.other_agent,
            motivation="sale",
            client_price="210000",
            estimated_price="205000",
        )
        self.own_order = Order.objects.create(
            buyer=self.own_contact,
            agent=self.agent,
            operation_type="sale",
            max_price="250000",
            payment_type="cash",
            property_type="flat",
        )
        self.other_order = Order.objects.create(
            buyer=self.other_contact,
            agent=self.other_agent,
            operation_type="sale",
            max_price="260000",
            payment_type="financing",
            property_type="house",
        )
        self.other_appointment = Appointment.objects.create(
            related_property=self.other_property,
            contact=self.other_contact,
            agent=self.other_agent,
            appointment_type="acquisition",
            date=date(2026, 9, 1),
            time=time(10, 0),
            end_time=time(11, 0),
            news=self.other_news,
        )
        self.other_task = Task.objects.create(
            task_type="custom",
            title="Tarea ajena",
            assigned_to=self.other_agent,
            created_by=self.manager,
        )
        self.other_sale = Sale.objects.create(
            related_property=self.other_property,
            buyer=self.other_contact,
            agent=self.other_agent,
            sale_price="220000",
        )

    def test_agent_can_view_all_contacts_but_only_change_own(self):
        self.client.force_login(self.agent)

        self.assertEqual(
            self.client.get(reverse("contact_detail", args=[self.other_contact.pk])).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("contact_update", args=[self.own_contact.pk])).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("contact_update", args=[self.other_contact.pk])).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse("contact_delete", args=[self.other_contact.pk])).status_code,
            403,
        )

    def test_manager_can_change_any_contact(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("contact_update", args=[self.other_contact.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("assigned_agent", response.context["form"].fields)

    def test_agent_cannot_change_property_created_by_another_agent(self):
        self.client.force_login(self.agent)

        self.assertEqual(
            self.client.get(reverse("property_detail", args=[self.other_property.pk])).status_code,
            200,
        )
        for view_name in (
            "property_update",
            "property_delete",
            "add_owner_to_property",
            "create_owner_for_property",
        ):
            with self.subTest(view=view_name):
                self.assertEqual(
                    self.client.get(
                        reverse(view_name, args=[self.other_property.pk])
                    ).status_code,
                    403,
                )
        self.assertEqual(
            self.client.post(
                reverse("property_add_comment", args=[self.other_property.pk]),
                {"text": "Comentario no autorizado"},
            ).status_code,
            403,
        )

    def test_agent_cannot_open_or_mutate_another_agents_news(self):
        self.client.force_login(self.agent)

        for view_name in ("news_detail", "news_update", "news_delete"):
            with self.subTest(view=view_name):
                self.assertEqual(
                    self.client.get(reverse(view_name, args=[self.other_news.pk])).status_code,
                    404,
                )
        self.assertEqual(
            self.client.post(
                reverse("news_add_comment", args=[self.other_news.pk]),
                {"text": "Comentario no autorizado"},
            ).status_code,
            404,
        )

    def test_agent_cannot_open_or_mutate_another_agents_order(self):
        self.client.force_login(self.agent)

        for view_name in ("order_detail", "order_update", "order_delete"):
            with self.subTest(view=view_name):
                self.assertEqual(
                    self.client.get(reverse(view_name, args=[self.other_order.pk])).status_code,
                    404,
                )

    def test_agent_cannot_schedule_events_on_another_agents_processes(self):
        self.client.force_login(self.agent)

        self.assertEqual(
            self.client.get(
                reverse("create_appointment", args=[self.other_news.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("create_call", args=[self.other_news.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("create_order_sale_appointment", args=[self.other_order.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("appointment_update", args=[self.other_appointment.pk])
            ).status_code,
            404,
        )

    def test_agent_task_form_only_accepts_self_assignment(self):
        self.client.force_login(self.agent)

        create_response = self.client.get(reverse("task_create"))
        update_response = self.client.get(
            reverse("task_update", args=[self.other_task.pk])
        )

        assigned_field = create_response.context["form"].fields["assigned_to"]
        self.assertQuerySetEqual(assigned_field.queryset, [self.agent])
        self.assertEqual(assigned_field.widget.input_type, "hidden")
        self.assertEqual(update_response.status_code, 404)

    def test_agent_cannot_change_another_agents_sale_or_use_direct_creation(self):
        self.client.force_login(self.agent)

        self.assertEqual(
            self.client.post(
                reverse("sale_update_status", args=[self.other_sale.pk]),
                {"status": "cancelled"},
            ).status_code,
            404,
        )
        self.assertEqual(self.client.get(reverse("sale_create")).status_code, 403)

    def test_manager_can_access_office_records_and_direct_sale_creation(self):
        self.client.force_login(self.manager)

        self.assertEqual(
            self.client.get(reverse("news_update", args=[self.other_news.pk])).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("order_update", args=[self.other_order.pk])).status_code,
            200,
        )
        self.assertEqual(self.client.get(reverse("sale_create")).status_code, 200)
