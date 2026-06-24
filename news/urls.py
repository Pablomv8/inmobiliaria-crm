from django.urls import path

from . import views

urlpatterns = [

    path(
        "create/<int:property_id>/",
        views.news_create,
        name="news_create"
    ),
    path(
        "<int:pk>/",
        views.news_detail,
        name="news_detail"
    ),

    path(
        "<int:pk>/comment/",
        views.news_add_comment,
        name="news_add_comment"
    ),
]