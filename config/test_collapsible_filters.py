from django.template.loader import get_template
from django.test import SimpleTestCase


class CollapsibleListFilterTests(SimpleTestCase):
    def test_main_list_filters_are_collapsible_on_mobile(self):
        template_names = [
            "activities/activity_list.html",
            "calendar_app/appointment_list.html",
            "contacts/list.html",
            "dashboard/alerts.html",
            "goals/list.html",
            "listings/list.html",
            "news/list.html",
            "orders/list.html",
            "properties/list.html",
            "properties/map.html",
            "sales/rental_contract_list.html",
            "sales/sale_list.html",
            "tasks/task_list.html",
        ]

        for template_name in template_names:
            with self.subTest(template=template_name):
                source = get_template(template_name).template.source
                self.assertIn("data-list-filters", source)

    def test_base_template_provides_filter_toggle_behaviour(self):
        source = get_template("base.html").template.source

        self.assertIn("form[data-list-filters]", source)
        self.assertIn("Mostrar filtros", source)
        self.assertIn("Ocultar filtros", source)
        self.assertIn("data-list-filter-panel", source)
