from django.urls import path
from .views import dashboard, team_member_detail, team_overview


urlpatterns = [
    path('', dashboard, name = 'dashboard'),
    path("team/", team_overview, name="team_overview"),
    path("team/<int:pk>/", team_member_detail, name="team_member_detail"),
]
