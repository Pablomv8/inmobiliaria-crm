from django.template.loader import get_template
from django.test import SimpleTestCase


class DashboardResponsiveLayoutTests(SimpleTestCase):
    def test_personal_portfolio_is_compact_on_mobile(self):
        source = get_template("dashboard/home.html").template.source

        self.assertIn("grid min-w-0 grid-cols-2", source)
        self.assertGreaterEqual(
            source.count("hidden text-xs text-gray-500 sm:block"),
            7,
        )
        self.assertIn("sm:rounded-2xl sm:p-5", source)

    def test_dashboard_containers_cannot_expand_the_page_width(self):
        home = get_template("dashboard/home.html").template.source
        action_center = get_template(
            "dashboard/partials/action_center.html"
        ).template.source
        navbar = get_template("partials/navbar.html").template.source

        self.assertIn("w-full min-w-0 max-w-full", home)
        self.assertIn("w-full min-w-0 max-w-full", action_center)
        self.assertIn("w-full min-w-0 max-w-full", navbar)

    def test_office_summary_partials_are_width_safe(self):
        template_names = [
            "dashboard/partials/action_center.html",
            "dashboard/partials/economics.html",
            "dashboard/partials/funnel.html",
            "dashboard/partials/goals.html",
        ]

        for template_name in template_names:
            with self.subTest(template=template_name):
                source = get_template(template_name).template.source
                self.assertIn("w-full min-w-0 max-w-full", source)

    def test_daily_work_summary_is_compact_on_mobile(self):
        source = get_template("dashboard/daily_work.html").template.source

        self.assertIn("grid min-w-0 grid-cols-2", source)
        self.assertEqual(source.count("hidden text-xs"), 4)
        self.assertIn("sm:rounded-2xl sm:p-5", source)

    def test_worker_summary_is_compact_on_mobile(self):
        source = get_template(
            "dashboard/team_member_detail.html"
        ).template.source

        self.assertIn("grid min-w-0 grid-cols-2 gap-2", source)
        self.assertEqual(
            source.count("hidden text-xs text-gray-400 sm:block"),
            4,
        )
        self.assertIn("text-xl font-bold sm:text-2xl", source)

    def test_home_omits_recent_activity_for_both_dashboard_modes(self):
        source = get_template("dashboard/home.html").template.source

        self.assertNotIn("Actividad reciente", source)
        self.assertNotIn("recent_activities", source)

    def test_recent_assignments_cannot_overflow_on_mobile(self):
        source = get_template("dashboard/home.html").template.source

        self.assertIn(
            "grid w-full min-w-0 max-w-full gap-4 overflow-hidden",
            source,
        )
        self.assertEqual(
            source.count(
                "w-full min-w-0 max-w-full overflow-hidden rounded-2xl"
            ),
            2,
        )
        self.assertGreaterEqual(
            source.count("flex w-full min-w-0 max-w-full"),
            2,
        )
