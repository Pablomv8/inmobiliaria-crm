from django.urls import path
from . import views

urlpatterns = [
    path(
        "create/<int:news_id>/<str:type>/",
        views.appointment_create,
        name="appointment_create"
    ),

]