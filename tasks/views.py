from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import Task
from contacts.models import Contact
from django.http import HttpResponseForbidden
from django.contrib.auth import get_user_model

User = get_user_model()

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

        qs = Task.objects.select_related(
            "assigned_to",
            "contact"
        )

        # agentes solo ven sus tareas
        if user.role == "agent":
            qs = qs.filter(assigned_to=user)

        # FILTRO ESTADO
        status = self.request.GET.get("status")

        if status:
            qs = qs.filter(status=status)

        # FILTRO PRIORIDAD
        priority = self.request.GET.get("priority")

        if priority:
            qs = qs.filter(priority=priority)

        # FILTRO AGENTE
        agent = self.request.GET.get("agent")

        if agent:
            qs = qs.filter(assigned_to_id=agent)

        # BÚSQUEDA
        search = self.request.GET.get("search")

        if search:
            qs = qs.filter(title__icontains=search)

        ordering = self.request.GET.get("ordering")

        if ordering == "due_date":
            qs = qs.order_by("due_date")

        elif ordering == "priority":
            qs = qs.order_by("-priority")

        elif ordering == "status":
            qs = qs.order_by("status")

        else:
            qs = qs.order_by("-created_at")

        return qs.order_by("-created_at")
        
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["agents"] = User.objects.filter(role="agent")

        return context

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

# -----------------------
# cambiar estado (solo admin/manager)
# -----------------------
@login_required
def task_update_status(request, pk):

    task = get_object_or_404(Task, pk=pk)

    if request.method == "POST":

        # agentes solo pueden modificar sus tareas
        if request.user.role == "agent" and task.assigned_to != request.user:
            return redirect("task_list")

        status = request.POST.get("status")

        if status in dict(Task.STATUS_CHOICES):
            task.status = status
            task.save()

    return redirect("task_list")


@login_required
def task_update_priority(request, pk):

    task = get_object_or_404(Task, pk=pk)

    if request.method == "POST":

        # agentes solo pueden modificar sus tareas
        if request.user.role == "agent" and task.assigned_to != request.user:
            return redirect("task_list")

        priority = request.POST.get("priority")

        if priority in dict(Task.PRIORITY_CHOICES):
            task.priority = priority
            task.save()

    return redirect("task_list")