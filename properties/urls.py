from django.urls import path

from .views import (
    property_list,
    property_detail,
    property_create,
    property_update,
    property_delete,
)

urlpatterns = [

    path('', property_list, name='properties'),

    path('new/', property_create, name='property_create'),

    path('<int:pk>/', property_detail, name='property_detail'),

    path('<int:pk>/edit/', property_update, name='property_update'),

    path('<int:pk>/delete/', property_delete, name='property_delete'),
]