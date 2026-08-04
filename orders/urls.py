from django.urls import path

from . import views


urlpatterns = [
    path("", views.order_list, name="order_list"),
    path("new/", views.order_create, name="order_create"),
    path(
        "buyer/<int:buyer_id>/new/",
        views.order_create,
        name="order_create_for_buyer",
    ),
    path("<int:pk>/", views.order_detail, name="order_detail"),
    path(
        "<int:pk>/comments/add/",
        views.order_add_comment,
        name="order_add_comment",
    ),
    path("<int:pk>/edit/", views.order_update, name="order_update"),
    path("<int:pk>/delete/", views.order_delete, name="order_delete"),
]
