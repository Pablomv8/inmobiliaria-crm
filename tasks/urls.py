from django.urls import path
from .views import (
    TaskListView,
    TaskCreateView,
    TaskUpdateView,
    task_delete,
    TaskDetailView,
    task_update_status,
    task_update_priority
)

urlpatterns = [
    path("", TaskListView.as_view(), name="task_list"),
    path("create/", TaskCreateView.as_view(), name="task_create"),
    path("<int:pk>/", TaskDetailView.as_view(), name="task_detail"),
    path("<int:pk>/edit/", TaskUpdateView.as_view(), name="task_update"),
    path("<int:pk>/delete/", task_delete, name="task_delete"),
    path("<int:pk>/update-status",task_update_status, name="task_update_status"),
    path("<int:pk>/update-priority",task_update_priority, name="task_update_priority"),

]