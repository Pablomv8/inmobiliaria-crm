from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import Task
from contacts.models import Contact
from django.http import HttpResponseForbidden

def dispatch(self, request, *args, **kwargs):
    user = request.user

    if user.role not in ["admin", "manager"]:
        return HttpResponseForbidden("No tienes permisos")

    return super().dispatch(request, *args, **kwargs)

# -----------------------
# LISTADO
# -----------------------
class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/task_list.html"
    context_object_name = "tasks"

    def get_queryset(self):
        user = self.request.user

        qs = Task.objects.select_related("assigned_to", "contact").all()

        if user.role == "agent":
            qs = qs.filter(assigned_to=user)

        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)

        return qs
    


# -----------------------
# DETALLE
# -----------------------
class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/task_detail.html"
    context_object_name = "task"


# -----------------------
# CREAR TAREA (MANAGER / ADMIN)
# -----------------------
class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    fields = [
        "title",
        "description",
        "contact",
        "property",
        "assigned_to",
        "status",
        "priority",
        "due_date",
    ]
    template_name = "tasks/task_form.html"
    success_url = reverse_lazy("task_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


# -----------------------
# EDITAR TAREA
# -----------------------
class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    fields = [
        "title",
        "description",
        "assigned_to",
        "status",
        "priority",
        "due_date",
    ]
    template_name = "tasks/task_form.html"
    success_url = reverse_lazy("task_list")

    def get_queryset(self):
        user = self.request.user

        if user.role in ["admin", "manager"]:
            return Task.objects.all()

        # agentes solo pueden editar sus tareas
        return Task.objects.filter(assigned_to=user)


# -----------------------
# BORRAR TAREA (solo admin/manager)
# -----------------------
@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if request.user.role not in ["admin", "manager"]:
        return redirect("task_list")

    if request.method == "POST":
        task.delete()
        return redirect("task_list")

    return redirect("task_list")