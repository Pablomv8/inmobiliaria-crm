from django.urls import path
from .views import (
    administration,
    alert_center,
    commercial_funnel_data,
    daily_work,
    dashboard,
    team_member_detail,
    team_overview,
)


urlpatterns = [
    path('', dashboard, name = 'dashboard'),
    path("alerts/", alert_center, name="alert_center"),
    path("today/", daily_work, name="daily_work"),
    path("funnel-data/", commercial_funnel_data, name="dashboard_funnel_data"),
    path("administration/", administration, name="administration"),
    path("team/", team_overview, name="team_overview"),
    path("team/<int:pk>/", team_member_detail, name="team_member_detail"),
]
