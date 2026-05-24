from django.urls import path
from .views import contact_list, contact_create, contact_detail,contact_delete, contact_update

urlpatterns = [
    path('', contact_list, name='contact_list'),

    path('new/', contact_create, name='contact_create'),

    path('<int:pk>/', contact_detail, name='contact_detail'),

    path('<int:pk>/edit/', contact_update, name='contact_update'),

    path('<int:pk>/delete/', contact_delete, name='contact_delete'),
    
]