from django.urls import path
from .views import contact_list

urlpatterns = [
    path('contacts/', contact_list, name='contact_list'),
]