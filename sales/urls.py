from django.urls import path

from .views import (
    SaleListView,
    SaleCreateView,
    sale_update_status,
    sale_list,
)

urlpatterns = [
    path(
        "",
        sale_list,
        name="sale_list"
    ),

    path(
        "create/",
        SaleCreateView.as_view(),
        name="sale_create"
    ),

    path(
        "<int:pk>/update-status/",
        sale_update_status,
        name="sale_update_status"
    ),
]