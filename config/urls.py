"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from config.health import live, ready
from config.pwa_views import manifest, offline, service_worker

handler400 = "config.error_views.bad_request"
handler403 = "config.error_views.permission_denied"
handler404 = "config.error_views.page_not_found"
handler500 = "config.error_views.server_error"
from .comment_views import comment_edit, comment_hide

urlpatterns = [
    path("manifest.webmanifest", manifest, name="pwa_manifest"),
    path("service-worker.js", service_worker, name="pwa_service_worker"),
    path("offline/", offline, name="pwa_offline"),
    path("health/live/", live, name="health_live"),
    path("health/ready/", ready, name="health_ready"),
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('contacts/', include('contacts.urls')),
    path('properties/', include('properties.urls')),
    path('', include('users.urls')),
    path("tasks/", include("tasks.urls")),
    path("activities/", include("activities.urls")),
    path("sales/", include('sales.urls')),
    path("news/",include("news.urls")),
    path("calendar/", include("calendar_app.urls")),
    path("listings/", include("listings.urls")),
    path("orders/", include("orders.urls")),
    path("goals/", include("goals.urls")),
    path("select2/", include("django_select2.urls")),
    path("comments/<str:kind>/<int:pk>/edit/", comment_edit, name="comment_edit"),
    path("comments/<str:kind>/<int:pk>/hide/", comment_hide, name="comment_hide"),
]
