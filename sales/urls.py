from django.urls import path

from .views import (
    SaleListView,
    SaleCreateView,
    sale_update_status,
    sale_list,
    contract_signing_decision,
    create_closing_from_contract,
    rental_contract_detail,
    rental_contract_reassign,
    rental_contract_list,
    sale_detail,
    sale_reassign,
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
        "contract-appointments/<int:appointment_id>/signed/",
        contract_signing_decision,
        name="contract_signing_decision",
    ),
    path(
        "contract-appointments/<int:appointment_id>/close/",
        create_closing_from_contract,
        name="create_closing_from_contract",
    ),
    path("<int:pk>/", sale_detail, name="sale_detail"),
    path("<int:pk>/reassign/", sale_reassign, name="sale_reassign"),
    path(
        "rentals/",
        rental_contract_list,
        name="rental_contract_list",
    ),
    path(
        "rentals/<int:pk>/",
        rental_contract_detail,
        name="rental_contract_detail",
    ),
    path(
        "rentals/<int:pk>/reassign/",
        rental_contract_reassign,
        name="rental_contract_reassign",
    ),

    path(
        "<int:pk>/update-status/",
        sale_update_status,
        name="sale_update_status"
    ),
]
