from django.urls import path

from .views import (
    property_list,
    property_detail,
    property_create,
    property_update,
    property_delete,
    property_update_status,
    create_owner_for_property,
    add_owner_to_property,
)

urlpatterns = [

    path('', property_list, name='properties'),

    path('new/', property_create, name='property_create'),

    path('<int:pk>/', property_detail, name='property_detail'),

    path('<int:pk>/edit/', property_update, name='property_update'),

    path('<int:pk>/delete/', property_delete, name='property_delete'),

    path('<int:pk>/update_status/', property_update_status, name = 'property_update_status' ),

    path(
        "properties/<int:property_id>/owners/new/",
        create_owner_for_property,
        name="create_owner_for_property"
    ),
    path(
        "properties/<int:property_id>/owners/add/",
        add_owner_to_property,
        name="add_owner_to_property"
    ),
    
]