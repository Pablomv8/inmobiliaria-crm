from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from contacts.models import Contact
from properties.models import Zone

from .models import Order, OrderComment


class OrderCrudTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="orders-agent",
            password="test-password",
        )
        self.contact_agent = get_user_model().objects.create_user(
            username="buyer-contact-agent",
            password="test-password",
        )
        self.manager = get_user_model().objects.create_user(
            username="orders-manager",
            password="test-password",
            role="manager",
        )
        self.buyer = Contact.objects.create(
            name="Compradora",
            phone="600000001",
            contact_type="buyer",
            assigned_agent=self.contact_agent,
        )
        self.owner = Contact.objects.create(
            name="Propietario",
            phone="600000002",
            contact_type="owner",
        )
        self.zone = Zone.objects.create(name="Centro")
        self.client.force_login(self.user)

    def order_data(self):
        return {
            "buyer": self.buyer.pk,
            "operation_type": "sale",
            "zone": self.zone.pk,
            "max_price": "275000",
            "payment_type": "financing",
            "property_type": "flat",
            "bedrooms": 3,
            "bathrooms": 2,
            "notes": "Con terraza.",
        }

    def test_create_order_for_buyer(self):
        data = self.order_data()
        data.pop("buyer")
        response = self.client.post(
            reverse("order_create_for_buyer", args=[self.buyer.pk]),
            data,
        )

        order = Order.objects.get()
        self.assertRedirects(response, reverse("order_detail", args=[order.pk]))
        self.assertEqual(order.buyer, self.buyer)
        self.assertEqual(order.agent, self.user)
        self.assertNotEqual(order.agent, self.buyer.assigned_agent)

    def test_general_form_rejects_owner_as_buyer(self):
        data = self.order_data()
        data["buyer"] = self.owner.pk
        response = self.client.post(reverse("order_create"), data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())

    def test_order_requires_purchase_or_rental_operation(self):
        data = self.order_data()
        data.pop("operation_type")

        response = self.client.post(reverse("order_create"), data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "operation_type",
            "Este campo es obligatorio.",
        )
        self.assertFalse(Order.objects.exists())

    def test_rental_order_is_saved_displayed_and_filterable(self):
        data = self.order_data()
        data["operation_type"] = "rent"
        data["max_price"] = "1500"

        response = self.client.post(reverse("order_create"), data)
        order = Order.objects.get()

        self.assertRedirects(response, reverse("order_detail", args=[order.pk]))
        self.assertEqual(order.operation_type, "rent")

        detail_response = self.client.get(reverse("order_detail", args=[order.pk]))
        list_response = self.client.get(
            reverse("order_list"),
            {"operation_type": "rent"},
        )
        purchase_response = self.client.get(
            reverse("order_list"),
            {"operation_type": "sale"},
        )
        self.assertContains(detail_response, "Alquiler")
        self.assertContains(list_response, self.buyer.name)
        self.assertNotContains(purchase_response, self.buyer.name)

    def test_orders_can_be_ordered_by_highest_budget(self):
        lower_budget = Order.objects.create(
            buyer=self.buyer,
            agent=self.user,
            operation_type="sale",
            max_price="150000",
            payment_type="cash",
            property_type="flat",
        )
        higher_budget = Order.objects.create(
            buyer=self.buyer,
            agent=self.user,
            operation_type="sale",
            max_price="450000",
            payment_type="financing",
            property_type="house",
        )

        response = self.client.get(
            reverse("order_list"),
            {"ordering": "budget_desc"},
        )

        self.assertEqual(response.context["orders"][0], higher_budget)
        self.assertNotEqual(response.context["orders"][0], lower_budget)
        self.assertContains(response, 'option value="budget_desc" selected', html=False)

    def test_order_forms_use_grouped_recent_style(self):
        general_response = self.client.get(reverse("order_create"))
        buyer_response = self.client.get(
            reverse("order_create_for_buyer", args=[self.buyer.pk])
        )

        for response in (general_response, buyer_response):
            with self.subTest(path=response.request["PATH_INFO"]):
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "1. Cliente")
                self.assertContains(response, "2. Criterios de búsqueda")
                self.assertContains(response, "3. Preferencias adicionales")
                self.assertContains(response, "rounded-3xl")

        self.assertContains(general_response, 'name="buyer"', html=False)
        self.assertNotContains(buyer_response, 'name="buyer"', html=False)
        self.assertContains(buyer_response, self.buyer.name)

    def test_update_and_delete_order(self):
        order = Order.objects.create(
            buyer=self.buyer,
            agent=self.user,
            operation_type="sale",
            max_price="200000",
            payment_type="cash",
            property_type="local",
        )
        data = self.order_data()
        response = self.client.post(reverse("order_update", args=[order.pk]), data)
        order.refresh_from_db()

        self.assertRedirects(response, reverse("order_detail", args=[order.pk]))
        self.assertEqual(order.property_type, "flat")

        response = self.client.post(reverse("order_delete", args=[order.pk]))
        self.assertRedirects(response, reverse("order_list"))
        self.assertFalse(Order.objects.exists())

    def test_manager_can_reassign_order(self):
        order = Order.objects.create(
            buyer=self.buyer,
            agent=self.user,
            operation_type="sale",
            max_price="200000",
            payment_type="cash",
            property_type="local",
        )
        self.client.force_login(self.manager)
        data = self.order_data()
        data["agent"] = self.contact_agent.pk

        response = self.client.post(reverse("order_update", args=[order.pk]), data)

        order.refresh_from_db()
        self.assertRedirects(response, reverse("order_detail", args=[order.pk]))
        self.assertEqual(order.agent, self.contact_agent)

    def test_manager_must_assign_an_agent_to_new_order(self):
        self.client.force_login(self.manager)
        data = self.order_data()

        response = self.client.post(reverse("order_create"), data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.assertFormError(
            response.context["form"],
            "agent",
            "Selecciona la persona responsable del pedido.",
        )

    def test_manager_is_selected_by_default_as_order_agent(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse("order_create"))

        self.assertEqual(
            response.context["form"]["agent"].value(),
            self.manager.pk,
        )

    def test_agent_cannot_reassign_order_through_post_data(self):
        order = Order.objects.create(
            buyer=self.buyer,
            agent=self.user,
            operation_type="sale",
            max_price="200000",
            payment_type="cash",
            property_type="local",
        )
        data = self.order_data()
        data["agent"] = self.contact_agent.pk

        self.client.post(reverse("order_update", args=[order.pk]), data)

        order.refresh_from_db()
        self.assertEqual(order.agent, self.user)

    def test_add_comment_to_order(self):
        order = Order.objects.create(
            buyer=self.buyer,
            agent=self.user,
            operation_type="sale",
            max_price="250000",
            payment_type="financing",
            property_type="flat",
        )

        response = self.client.post(
            reverse("order_add_comment", args=[order.pk]),
            {"text": "Busca una vivienda con terraza y buena iluminación."},
            follow=True,
        )

        comment = OrderComment.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(comment.order, order)
        self.assertEqual(comment.user, self.user)
        self.assertEqual(
            comment.text,
            "Busca una vivienda con terraza y buena iluminación.",
        )
        self.assertContains(response, comment.text)

    def test_empty_order_comment_is_rejected(self):
        order = Order.objects.create(
            buyer=self.buyer,
            agent=self.user,
            operation_type="rent",
            max_price="250000",
            payment_type="cash",
            property_type="house",
        )

        response = self.client.post(
            reverse("order_add_comment", args=[order.pk]),
            {"text": "   "},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(OrderComment.objects.exists())
        self.assertContains(
            response,
            "El comentario no puede estar vacío.",
            status_code=400,
        )
