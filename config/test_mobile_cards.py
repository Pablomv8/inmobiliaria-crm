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

    def test_task_cards_cannot_overflow_the_mobile_viewport(self):
        source = get_template("tasks/task_list.html").template.source

        self.assertIn(
            "mobile-card w-full min-w-0 max-w-full overflow-hidden",
            source,
        )
        self.assertIn("whitespace-normal break-words", source)
        self.assertIn("grid grid-cols-2 gap-2", source)
