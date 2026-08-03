from django.urls import path

from . import views

urlpatterns = [

    path(
        "",
        views.news_list,
        name="news_list"
    ),
    path(
        "new/",
        views.news_create,
        name="news_create_general"
    ),

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
        "<int:pk>/edit/",
        views.news_update,
        name="news_update"
    ),
    path(
        "<int:pk>/delete/",
        views.news_delete,
        name="news_delete"
    ),

    path(
        "<int:pk>/comment/",
        views.news_add_comment,
        name="news_add_comment"
    ),
]
