from django.test import TestCase

from .forms import PropertyForm
from .models import Property


class PropertyModelTests(TestCase):

    def test_property_only_uses_supported_types(self):
        self.assertEqual(
            Property.PROPERTY_TYPE_CHOICES,
            (
                ("flat", "Piso"),
                ("house", "Casa"),
                ("villa", "Villa"),
                ("office", "Oficina"),
                ("local", "Local"),
                ("solar", "Solar"),
                ("terreno", "Terreno"),
            ),
        )

    def test_property_no_longer_has_title_or_price_fields(self):
        field_names = {field.name for field in Property._meta.get_fields()}

        self.assertNotIn("title", field_names)
        self.assertNotIn("price", field_names)

    def test_property_form_no_longer_exposes_title_or_price(self):
        form = PropertyForm()

        self.assertNotIn("title", form.fields)
        self.assertNotIn("price", form.fields)

    def test_property_form_accepts_previous_and_new_types(self):
        for property_type in ("flat", "local", "solar", "terreno"):
            with self.subTest(property_type=property_type):
                form = PropertyForm(data={
                    "street": "Calle Mayor",
                    "number": "10",
                    "city": "Madrid",
                    "property_type": property_type,
                    "status": "prospect",
                })

                self.assertTrue(form.is_valid(), form.errors)
