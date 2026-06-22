from django.urls import path
from . import views
from listings.views import create_listing_from_appointment

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
    path(
        "available-slots/",
        views.available_slots,
        name="available_slots"
    ),
    path(
        "appointments/<int:appointment_id>/create-listing/",
        create_listing_from_appointment,
        name="create_listing"
    ),
    path(
        "appointments/<int:appointment_id>/status/<str:status>/",
        views.update_appointment_status,
        name="appointment_update_status"
    ),
    path(
        "calls/<int:call_id>/status/<str:status>/",
        views.update_call_status,
        name="call_update_status"
    ),
]