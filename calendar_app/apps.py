from django.apps import AppConfig


class CalendarAppConfig(AppConfig):
    name = 'calendar_app'

    def ready(self):
        from . import signals  # noqa: F401
