from datetime import date, datetime, time

from django import forms
from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils import formats, translation

from calendar_app.forms import AppointmentForm, CallForm, SaleAppointmentForm
from config.widgets import CRMDateInput, CRMDateTimeInput, CRMTimeInput
from listings.forms import ListingForm
from news.forms import NewsForm
from orders.forms import OrderForm
from sales.forms import SaleClosingForm, SaleForm


class SpanishFrontendTests(SimpleTestCase):
    def test_application_uses_spanish_formats_and_errors(self):
        self.assertEqual(settings.LANGUAGE_CODE, "es-es")

        with translation.override("es-es"):
            formatted = formats.date_format(
                datetime(2026, 9, 3, 17, 30),
                "DATETIME_FORMAT",
            )
            field = forms.CharField()

        self.assertEqual(
            formatted,
            "3 de septiembre de 2026 a las 17:30",
        )
        with self.assertRaisesMessage(
            forms.ValidationError,
            "Este campo es obligatorio.",
        ):
            field.clean("")

    def test_html_date_and_time_widgets_keep_browser_compatible_values(self):
        self.assertEqual(
            CRMDateInput().format_value(date(2026, 9, 3)),
            "2026-09-03",
        )
        self.assertEqual(
            CRMTimeInput().format_value(time(17, 30)),
            "17:30",
        )
        self.assertEqual(
            CRMDateTimeInput().format_value(datetime(2026, 9, 3, 17, 30)),
            "2026-09-03T17:30",
        )

    def test_main_forms_expose_spanish_labels(self):
        expected_labels = {
            OrderForm: {"buyer": "Comprador", "zone": "Zona"},
            NewsForm: {"agent": "Agente asignado"},
            ListingForm: {"agent": "Agente asignado"},
            SaleForm: {
                "related_property": "Inmueble",
                "buyer": "Comprador",
                "sale_price": "Precio de compra (€)",
                "notes": "Notas",
            },
            SaleClosingForm: {"sale_price": "Precio de compra (€)"},
            AppointmentForm: {
                "appointment_type": "Tipo de cita",
                "time": "Hora de inicio",
            },
            CallForm: {"date": "Fecha", "time": "Hora"},
            SaleAppointmentForm: {"listing": "Encargo"},
        }
        for form_class, labels in expected_labels.items():
            for field_name, label in labels.items():
                with self.subTest(form=form_class.__name__, field=field_name):
                    self.assertEqual(
                        form_class.base_fields[field_name].label,
                        label,
                    )

    def test_calendar_loads_spanish_locale_and_24_hour_clock(self):
        rendered = render_to_string(
            "calendar_app/calendar.html",
            {
                "selected_agent_ids": "[]",
                "agents": [],
                "agenda_by_day": [],
                "today_events": [],
            },
        )

        self.assertIn("locales/es.global.min.js", rendered)
        self.assertIn('today: "Hoy"', rendered)
        self.assertIn('hour12: false', rendered)
