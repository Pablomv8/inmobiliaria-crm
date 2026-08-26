from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from calendar_app.models import Appointment
from contacts.models import Contact
from goals.models import Goal
from listings.models import Listing
from news.models import News
from orders.models import Order
from properties.models import Property
from sales.models import Sale


class DashboardScopeTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.agent = user_model.objects.create_user(
            username="dashboard-agent",
            password="test-password",
            role="agent",
        )
        self.other_agent = user_model.objects.create_user(
            username="dashboard-other",
            password="test-password",
            role="agent",
        )
        self.manager = user_model.objects.create_user(
            username="dashboard-manager",
            password="test-password",
            role="manager",
        )
        self.agent_owner = Contact.objects.create(
            name="Propietaria dashboard",
            phone="600400001",
            contact_type="owner",
            assigned_agent=self.agent,
        )
        self.agent_buyer = Contact.objects.create(
            name="Compradora dashboard",
            phone="600400002",
            contact_type="buyer",
            assigned_agent=self.agent,
        )
        self.other_buyer = Contact.objects.create(
            name="Comprador de otro agente",
            phone="600400003",
            contact_type="buyer",
            assigned_agent=self.other_agent,
        )
        self.agent_property = Property.objects.create(
            street="Calle Dashboard",
            number="1",
            city="Madrid",
            property_type="flat",
        )
        other_property = Property.objects.create(
            street="Calle Dashboard",
            number="2",
            city="Madrid",
            property_type="house",
        )
        self.agent_listing = Listing.objects.create(
            property=self.agent_property,
            listing_type="sale",
            owner_price="200000",
            agency_price="210000",
            agreed_price="208000",
            price_diference="10000",
            owner=self.agent_owner,
            agent=self.agent,
        )
        Listing.objects.create(
            property=other_property,
            listing_type="sale",
            owner_price="250000",
            agency_price="260000",
            agreed_price="258000",
            price_diference="10000",
            agent=self.other_agent,
        )
        Order.objects.create(
            buyer=self.agent_buyer,
            agent=self.agent,
            operation_type="sale",
            max_price="230000",
            payment_type="financing",
            property_type="flat",
        )
        Order.objects.create(
            buyer=self.other_buyer,
            agent=self.other_agent,
            operation_type="rent",
            max_price="280000",
            payment_type="cash",
            property_type="house",
        )
        Appointment.objects.create(
            related_property=self.agent_property,
            contact=self.agent_buyer,
            agent=self.agent,
            appointment_type="sale",
            date=date(2026, 8, 20),
            time=time(10, 0),
            end_time=time(11, 0),
            listing=self.agent_listing,
        )
        News.objects.create(
            related_property=self.agent_property,
            agent=self.agent,
            motivation="sale",
            client_price="210000",
            estimated_price="205000",
        )
        News.objects.create(
            related_property=other_property,
            agent=self.other_agent,
            motivation="sale",
            client_price="260000",
            estimated_price="255000",
        )

    def test_agent_only_sees_personal_portfolio(self):
        self.client.force_login(self.agent)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["my_listings"], 1)
        self.assertEqual(response.context["my_active_listings"], 1)
        self.assertEqual(response.context["my_orders"], 1)
        self.assertEqual(response.context["my_contacts"], 2)
        self.assertEqual(response.context["my_scheduled_appointments"], 1)
        self.assertFalse(response.context["is_office_viewer"])
        self.assertNotIn("office_listings", response.context)
        self.assertContains(response, "Mi cartera")
        self.assertNotContains(response, "Vista global de la oficina")

    def test_dashboard_sums_commissions_as_money_without_percentage_calculation(self):
        Sale.objects.create(
            related_property=self.agent_property,
            buyer=self.agent_buyer,
            agent=self.agent,
            sale_price="250000.00",
            commission_amount="8400.00",
            sale_date=date(2026, 8, 15),
            status="signed",
        )

        self.client.force_login(self.agent)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["my_commission"], 8400)
        self.assertEqual(response.context["personal_economics"]["commission"], 8400)
        self.assertEqual(response.context["personal_economics"]["sale_volume"], 250000)

    def test_personal_dashboard_shows_actions_funnel_and_active_goals(self):
        today = timezone.localdate()
        goal = Goal.objects.create(
            name="Objetivo visible en dashboard",
            scope="individual",
            metric="news",
            target_count=3,
            start_date=today,
            end_date=today,
            created_by=self.manager,
        )
        goal.assignees.add(self.agent)
        self.client.force_login(self.agent)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Centro de acciones")
        self.assertContains(response, "Mi embudo comercial")
        self.assertContains(response, "Mi resumen económico")
        self.assertContains(response, "Mis objetivos activos")
        self.assertContains(response, goal.name)
        self.assertContains(response, "Evolución de mi cartera")
        self.assertContains(response, "Cumplimiento personal")
        self.assertContains(response, "Salud de mi cartera")
        self.assertContains(response, "¿Qué significa cada fase del embudo?")
        self.assertContains(response, "Noticias captadas")
        self.assertContains(response, "Encargos formalizados")
        self.assertContains(response, "Operaciones firmadas")
        self.assertEqual(
            response.context["personal_analytics"]["goals"],
            {
                "active": 1,
                "achieved": 0,
                "at_risk": 1,
                "percentage": 33,
            },
        )
        monthly = response.context["personal_analytics"]["monthly"]
        self.assertEqual(len(monthly["labels"]), 6)
        self.assertEqual(monthly["news"][-1], 1)
        self.assertEqual(monthly["listings"][-1], 1)
        self.assertEqual(monthly["orders"][-1], 1)
        funnel_counts = [
            stage["count"]
            for stage in response.context["personal_funnel"]["stages"]
        ]
        self.assertEqual(funnel_counts, [1, 1, 1, 0, 0, 0])
        self.assertEqual(
            [stage["width"] for stage in response.context["personal_funnel"]["stages"]],
            [100, 100, 100, 0, 0, 0],
        )
        health = response.context["personal_commercial_health"]
        self.assertEqual(health["aging"]["counts"], [3, 0, 0, 0])
        self.assertEqual(health["aging"]["fresh_percentage"], 100)
        self.assertEqual(health["listings"]["total"], 1)
        self.assertEqual(health["listings"]["needs_attention"], 1)
        self.assertEqual(health["listings"]["without_recent_follow_up"], 1)
        order_alert = next(
            item
            for item in response.context["personal_action_items"]
            if item["label"] == "Pedidos sin cita de venta"
        )
        self.assertEqual(order_alert["count"], 1)
        self.assertContains(response, 'data-funnel-scope="personal"', html=False)
        self.assertContains(response, reverse("dashboard_funnel_data"))
        self.assertContains(response, "/static/dashboard-funnel.js")

    def test_personal_funnel_data_can_be_updated_without_rendering_dashboard(self):
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("dashboard_funnel_data"),
            {
                "scope": "personal",
                "funnel_from": "2026-08-20",
                "funnel_to": "2026-08-20",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            [stage["count"] for stage in data["stages"]],
            [0, 0, 1, 0, 0, 0],
        )
        self.assertEqual(data["period"]["from_value"], "2026-08-20")
        self.assertEqual(data["period"]["to_value"], "2026-08-20")

    def test_agent_cannot_request_office_funnel_data(self):
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("dashboard_funnel_data"),
            {"scope": "office"},
        )

        self.assertEqual(response.status_code, 403)

    def test_base_layout_has_no_search_and_only_one_scrollable_sidebar(self):
        self.client.force_login(self.agent)

        response = self.client.get(reverse("dashboard"))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('placeholder="Buscar..."', html)
        self.assertEqual(html.count("<aside"), 1)
        self.assertIn("min-h-0 flex-1 overflow-y-auto", html)
        self.assertIn("Abrir menú principal", html)

    def test_manager_sees_office_totals_and_every_user(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("dashboard"), {"view": "office"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_office_viewer"])
        self.assertEqual(response.context["office_listings"], 2)
        self.assertEqual(response.context["office_active_listings"], 2)
        self.assertEqual(response.context["office_orders"], 2)
        self.assertEqual(response.context["office_contacts"], 3)
        self.assertEqual(len(response.context["user_rows"]), 3)
        self.assertContains(response, "Vista global de la oficina")
        self.assertContains(response, "dashboard-agent")
        self.assertContains(response, "dashboard-other")
        self.assertContains(response, "Acciones de la oficina")
        self.assertContains(response, "Embudo comercial global")
        self.assertContains(response, "Resumen económico global")
        self.assertIn("office_goal_rows", response.context)
        self.assertContains(response, "Evolución comercial de la oficina")
        self.assertContains(response, "Comparación de actividad por agente")
        self.assertContains(response, "Salud comercial de la oficina")
        self.assertIn("office_commercial_health", response.context)
        comparison = response.context["agent_comparison"]
        self.assertIn("dashboard-agent", comparison["labels"])
        self.assertIn("dashboard-other", comparison["labels"])
        self.assertIn("dashboard-manager", comparison["labels"])
        self.assertEqual(len(comparison["contacts"]), len(comparison["labels"]))
        self.assertEqual(
            set(response.context["agent_comparisons"]),
            {"7", "30", "90"},
        )
        self.assertContains(response, 'id="agent-comparison-period"', html=False)
        self.assertContains(response, 'id="agent-comparisons-data"', html=False)
        self.assertNotContains(response, "this.form.submit()")
        self.assertContains(response, "comparisonChart.update()")

    def test_commercial_health_detects_stale_opportunities(self):
        stale_at = timezone.now() - timedelta(days=40)
        News.objects.filter(agent=self.agent).update(created_at=stale_at)
        Listing.objects.filter(agent=self.agent).update(created_at=stale_at)
        Order.objects.filter(agent=self.agent).update(
            created_at=stale_at,
            updated_at=stale_at,
        )
        Appointment.objects.filter(agent=self.agent).update(created_at=stale_at)
        self.client.force_login(self.agent)

        response = self.client.get(reverse("dashboard"))

        aging = response.context["personal_commercial_health"]["aging"]
        self.assertEqual(aging["counts"], [0, 0, 0, 3])
        self.assertEqual(aging["stale"], 3)
        self.assertEqual(aging["fresh_percentage"], 0)

    def test_commercial_health_groups_appointment_results(self):
        sale_appointment = Appointment.objects.get(agent=self.agent)
        sale_appointment.date = timezone.localdate()
        sale_appointment.status = "completed"
        sale_appointment.result_success = True
        sale_appointment.save(update_fields=["date", "status", "result_success"])
        Appointment.objects.create(
            related_property=self.agent_property,
            contact=self.agent_owner,
            agent=self.agent,
            appointment_type="acquisition",
            date=timezone.localdate(),
            time=time(12, 0),
            end_time=time(13, 0),
            status="cancelled",
        )
        self.client.force_login(self.agent)

        response = self.client.get(reverse("dashboard"))

        outcomes = response.context["personal_commercial_health"]["appointments"]
        self.assertEqual(outcomes["labels"], ["Adquisición", "Venta"])
        self.assertEqual(outcomes["successful"], [0, 1])
        self.assertEqual(outcomes["cancelled"], [1, 0])
        self.assertEqual(outcomes["total"], 2)
        self.assertEqual(outcomes["success_rate"], 100)

    def test_manager_can_choose_personal_office_or_combined_dashboard(self):
        self.client.force_login(self.manager)

        personal_response = self.client.get(reverse("dashboard"))
        office_response = self.client.get(
            reverse("dashboard"),
            {"view": "office"},
        )
        combined_response = self.client.get(
            reverse("dashboard"),
            {"view": "both"},
        )

        self.assertEqual(personal_response.context["dashboard_view"], "personal")
        self.assertContains(personal_response, "Mi cartera")
        self.assertNotContains(personal_response, "Vista global de la oficina")
        self.assertEqual(office_response.context["dashboard_view"], "office")
        self.assertNotContains(office_response, "Resumen personal")
        self.assertContains(office_response, "Vista global de la oficina")
        self.assertTrue(combined_response.context["show_personal_dashboard"])
        self.assertTrue(combined_response.context["show_office_dashboard"])
        self.assertContains(combined_response, "Resumen personal")
        self.assertContains(combined_response, "Vista global de la oficina")

    def test_office_dashboard_limits_goals_to_three_nearest_deadlines(self):
        today = timezone.localdate()
        goals = []
        for index in range(5):
            goal = Goal.objects.create(
                name=f"Objetivo oficina {index}",
                scope="individual",
                metric="news",
                target_count=2,
                start_date=today,
                end_date=today + timedelta(days=index + 1),
                created_by=self.manager,
            )
            goal.assignees.add(self.agent)
            goals.append(goal)
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("dashboard"),
            {"view": "office"},
        )

        displayed_goals = [
            row["goal"] for row in response.context["office_goal_rows"]
        ]
        self.assertEqual(displayed_goals, goals[:3])
        self.assertContains(response, "Los tres objetivos más próximos a vencer")
        self.assertNotContains(response, goals[3].name)

        administration_response = self.client.get(reverse("administration"))
        administration_goals = [
            row["goal"]
            for row in administration_response.context["office_goal_rows"]
        ]
        self.assertEqual(administration_goals, goals[:3])
        self.assertContains(
            administration_response,
            "Los tres objetivos más próximos a vencer",
        )
        self.assertNotContains(administration_response, goals[3].name)

    def test_manager_can_open_extended_administration(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse("administration"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Administración")
        self.assertContains(response, "Centro de acciones global")
        self.assertContains(response, "Estado de los inmuebles")
        self.assertContains(response, "Carga por usuario")
        self.assertContains(response, reverse("administration"))

    def test_agent_cannot_open_extended_administration(self):
        self.client.force_login(self.agent)

        response = self.client.get(reverse("administration"))

        self.assertEqual(response.status_code, 403)

    def test_personal_cards_link_to_logged_user_filters(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("dashboard"))
        html = response.content.decode()

        self.assertIn(
            f"{reverse('listing_list')}?agent={self.manager.pk}",
            html,
        )
        self.assertIn(
            f"{reverse('order_list')}?agent={self.manager.pk}",
            html,
        )
        self.assertIn(
            f"{reverse('news_list')}?agent={self.manager.pk}",
            html,
        )
        self.assertIn(
            f"{reverse('calendar')}?agents={self.manager.pk}",
            html,
        )

    def test_manager_can_filter_lists_by_user_from_global_view(self):
        self.client.force_login(self.manager)

        orders_response = self.client.get(
            reverse("order_list"),
            {"agent": self.agent.pk},
        )
        self.assertEqual(len(orders_response.context["orders"]), 1)
        self.assertEqual(
            orders_response.context["orders"][0].buyer,
            self.agent_buyer,
        )

        news_response = self.client.get(
            reverse("news_list"),
            {"agent": self.agent.pk},
        )
        self.assertEqual(len(news_response.context["news_items"]), 1)
        self.assertEqual(news_response.context["news_items"][0].agent, self.agent)

        contacts_response = self.client.get(
            reverse("contact_list"),
            {"agent": self.agent.pk},
        )
        self.assertEqual(len(contacts_response.context["contacts"]), 2)

        calendar_response = self.client.get(
            reverse("calendar"),
            {"agents": self.agent.pk},
        )
        self.assertEqual(
            calendar_response.context["selected_agent_ids"],
            [str(self.agent.pk)],
        )

    def test_agent_cannot_use_filter_to_see_another_agents_orders(self):
        self.client.force_login(self.agent)
        response = self.client.get(
            reverse("order_list"),
            {"agent": self.other_agent.pk},
        )

        self.assertEqual(len(response.context["orders"]), 1)
        self.assertEqual(response.context["orders"][0].buyer, self.agent_buyer)

    def test_manager_sees_worker_tracking_cards_with_assigned_metrics(self):
        inactive_agent = get_user_model().objects.create_user(
            username="inactive-agent",
            password="test-password",
            role="agent",
            is_active=False,
        )
        self.client.force_login(self.manager)

        response = self.client.get(reverse("team_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["worker_count"], 2)
        workers = [row["user"] for row in response.context["worker_rows"]]
        self.assertIn(self.agent, workers)
        self.assertIn(self.other_agent, workers)
        self.assertNotIn(self.manager, workers)
        self.assertNotIn(inactive_agent, workers)
        agent_row = next(
            row for row in response.context["worker_rows"]
            if row["user"] == self.agent
        )
        self.assertEqual(agent_row["contacts"], 2)
        self.assertEqual(agent_row["news"], 1)
        self.assertEqual(agent_row["listings"], 1)
        self.assertEqual(agent_row["orders"], 1)
        self.assertEqual(agent_row["scheduled_appointments"], 1)
        self.assertContains(
            response,
            reverse("team_member_detail", args=[self.agent.pk]),
        )

    def test_worker_tracking_is_paginated_without_changing_office_totals(self):
        get_user_model().objects.bulk_create([
            get_user_model()(
                username=f"worker-page-{index:02d}",
                role="agent",
                is_active=True,
            )
            for index in range(9)
        ])
        self.client.force_login(self.manager)

        response = self.client.get(reverse("team_overview"), {"page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["worker_count"], 11)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(response.context["page_obj"].paginator.count, 11)
        self.assertEqual(len(response.context["worker_rows"]), 1)
        self.assertContains(response, "Mostrando")

    def test_manager_sees_selected_worker_detail_and_recent_portfolio(self):
        today = timezone.localdate()
        goal = Goal.objects.create(
            name="Objetivo del agente en seguimiento",
            scope="individual",
            metric="news",
            target_count=1,
            start_date=today,
            end_date=today,
            created_by=self.manager,
        )
        goal.assignees.add(self.agent)
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("team_member_detail", args=[self.agent.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["worker"], self.agent)
        self.assertEqual(response.context["contacts_total"], 2)
        self.assertEqual(response.context["owners_total"], 1)
        self.assertEqual(response.context["buyers_total"], 1)
        self.assertEqual(response.context["news_total"], 1)
        self.assertEqual(response.context["listings_total"], 1)
        self.assertEqual(response.context["orders_total"], 1)
        self.assertEqual(response.context["scheduled_appointments"], 1)
        self.assertContains(response, "Indicadores de seguimiento")
        self.assertContains(response, "Objetivos activos del agente")
        self.assertContains(response, goal.name)
        self.assertContains(response, "Aportación del agente: 1")
        self.assertEqual(response.context["started_goals"], 1)
        self.assertEqual(response.context["achieved_goals"], 1)
        self.assertEqual(response.context["goal_completion_rate"], 100)
        self.assertContains(response, "Objetivos cumplidos")
        self.assertContains(response, "1 cumplidos de 1 objetivos iniciados")
        self.assertContains(response, "Embudo comercial del agente")
        self.assertContains(response, "¿Qué significa cada fase del embudo?")
        self.assertEqual(
            [stage["count"] for stage in response.context["worker_funnel"]["stages"]],
            [1, 1, 1, 0, 0, 0],
        )
        self.assertEqual(
            response.context["worker_funnel"]["stages"][0]["url"],
            f"{reverse('news_list')}?agent={self.agent.pk}",
        )
        self.assertEqual(
            response.context["worker_funnel"]["stages"][2]["url"],
            f"{reverse('calendar')}?agents={self.agent.pk}",
        )
        self.assertContains(response, self.agent_property.full_address)
        self.assertContains(
            response,
            f"{reverse('contact_list')}?agent={self.agent.pk}",
        )

    def test_worker_funnel_can_be_filtered_by_inclusive_date_range(self):
        News.objects.filter(agent=self.agent).update(
            created_at=timezone.make_aware(
                datetime(2026, 8, 19, 12, 0)
            )
        )
        Listing.objects.filter(agent=self.agent).update(
            created_at=timezone.make_aware(
                datetime(2026, 8, 21, 12, 0)
            )
        )
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("team_member_detail", args=[self.agent.pk]),
            {"funnel_from": "2026-08-20", "funnel_to": "2026-08-20"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [stage["count"] for stage in response.context["worker_funnel"]["stages"]],
            [0, 0, 1, 0, 0, 0],
        )
        self.assertEqual(
            response.context["worker_funnel"]["period"]["from_value"],
            "2026-08-20",
        )
        self.assertEqual(
            response.context["worker_funnel"]["period"]["to_value"],
            "2026-08-20",
        )
        self.assertContains(response, "Periodo aplicado:")
        self.assertContains(response, "20/08/2026")
        self.assertContains(response, 'data-funnel-scope="agent"', html=False)
        self.assertContains(
            response,
            f'data-funnel-agent-id="{self.agent.pk}"',
            html=False,
        )

        async_response = self.client.get(
            reverse("dashboard_funnel_data"),
            {
                "scope": "agent",
                "agent_id": self.agent.pk,
                "funnel_from": "2026-08-20",
                "funnel_to": "2026-08-20",
            },
        )
        self.assertEqual(async_response.status_code, 200)
        self.assertEqual(
            [stage["count"] for stage in async_response.json()["stages"]],
            [0, 0, 1, 0, 0, 0],
        )

    def test_agent_cannot_access_team_tracking(self):
        self.client.force_login(self.agent)

        overview_response = self.client.get(reverse("team_overview"))
        detail_response = self.client.get(
            reverse("team_member_detail", args=[self.other_agent.pk])
        )

        self.assertEqual(overview_response.status_code, 403)
        self.assertEqual(detail_response.status_code, 403)

    def test_only_active_agents_have_a_tracking_detail(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("team_member_detail", args=[self.manager.pk])
        )

        self.assertEqual(response.status_code, 404)
