from django.urls import path
from . import views

urlpatterns = [
    path("appointment/<int:news_id>/create/", views.create_appointment, name="create_appointment"),
    path("call/<int:news_id>/create/", views.create_call, name="create_call"),
    path("agenda/",views.agenda,name="agenda"),
    path(
        "",
        views.calendar_view,
        name="calendar"
    ),

    path(
        "events/",
        views.calendar_events,
        name="calendar_events"
    ),

    path(
        "calls/<int:pk>/",
        views.call_detail,
        name="call_detail"
    ),

    path(
        "appointments/<int:pk>/",
        views.appointment_detail,
        name="appointment_detail"
    ),
]