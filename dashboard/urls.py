from django.urls import path
from  .views import home,dashboard


urlpatterns = [
    path('', dashboard, name = 'dashboard'),

]