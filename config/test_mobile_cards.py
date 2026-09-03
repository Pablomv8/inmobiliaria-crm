from django.template.loader import get_template
from django.test import SimpleTestCase


class CompactMobileCardTests(SimpleTestCase):
    def test_main_lists_use_collapsible_mobile_cards(self):
        templates = [
            "calendar_app/appointment_list.html",
            "contacts/list.html",
            "listings/list.html",
            "news/list.html",
            "orders/list.html",
            "properties/list.html",
            "sales/rental_contract_list.html",
            "sales/sale_list.html",
            "tasks/task_list.html",
        ]

        for template_name in templates:
            with self.subTest(template=template_name):
                source = get_template(template_name).template.source
                self.assertIn('<details class="mobile-card', source)
                self.assertIn("mobile-card-toggle", source)
