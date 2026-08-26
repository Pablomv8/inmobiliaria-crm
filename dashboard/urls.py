from django.urls import path
from .views import (
    administration,
    commercial_funnel_data,
    dashboard,
    team_member_detail,
    team_overview,
)


urlpatterns = [
    path('', dashboard, name = 'dashboard'),
    path("funnel-data/", commercial_funnel_data, name="dashboard_funnel_data"),
    path("administration/", administration, name="administration"),
    path("team/", team_overview, name="team_overview"),
    path("team/<int:pk>/", team_member_detail, name="team_member_detail"),
]
