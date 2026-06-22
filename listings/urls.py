from django.urls import path
from . import views

urlpatterns = [

    path(
        "",
        views.listing_list,
        name="listing_list"
    ),

    path(
        "<int:listing_id>/",
        views.listing_detail,
        name="listing_detail"
    ),

    path(
        "create/<int:appointment_id>/",
        views.create_listing_from_appointment,
        name="create_listing"
    ),

]