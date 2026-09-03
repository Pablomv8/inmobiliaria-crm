from django.template.loader import get_template
from django.test import SimpleTestCase


class PropertyResponsiveDetailTests(SimpleTestCase):
    def test_characteristics_can_shrink_without_overflowing(self):
        source = get_template("properties/detail.html").template.source

        self.assertIn("grid min-w-0 grid-cols-2", source)
        self.assertGreaterEqual(source.count("min-w-0 break-words"), 12)
        self.assertIn("sm:grid-cols-3", source)

    def test_owner_actions_stack_on_small_screens(self):
        source = get_template("properties/detail.html").template.source

        self.assertIn("flex w-full min-w-0 flex-col", source)
        self.assertGreaterEqual(source.count("justify-center"), 2)
        self.assertIn("sm:w-auto sm:flex-row", source)
