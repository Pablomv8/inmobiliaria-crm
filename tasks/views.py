from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone


from .models import Task
from .forms import TaskForm
from properties.models import Zone
from django.contrib.auth import get_user_model
from activities.utils import log_activity
from activities.models import Activity

User = get_user_model()

# -----------------------
# LISTADO
# -----------------------
class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/task_list.html"
    context_object_name = "tasks"

    def get_queryset(self):

        user = self.request.user
        can_manage_all = (
            user.is_superuser
            or user.role in ["admin", "manager"]
        )

        qs = Task.objects.select_related(
            "assigned_to",
            "zone",
        )

        # agentes solo ven sus tareas
        if not can_manage_all:
            qs = qs.filter(assigned_to=user)

        # FILTRO ESTADO
        status = self.request.GET.get("status")

        if status:
            qs = qs.filter(status=status)

        # FILTRO PRIORIDAD
        priority = self.request.GET.get("priority")

        if priority:
            qs = qs.filter(priority=priority)

        task_type = self.request.GET.get("task_type")

        if task_type:
            qs = qs.filter(task_type=task_type)

        zone = self.request.GET.get("zone")

        if zone:
            qs = qs.filter(zone_id=zone)

        # FILTRO AGENTE
        agent = self.request.GET.get("agent")

        if agent and can_manage_all:
            qs = qs.filter(assigned_to_id=agent)

        # BÚSQUEDA
        search = self.request.GET.get("search")

        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(zone__name__icontains=search)
            )

        ordering = self.request.GET.get("ordering")

        if ordering == "due_date":
            qs = qs.order_by("due_date")

        elif ordering == "priority":
            qs = qs.order_by("-priority")

        elif ordering == "status":
            qs = qs.order_by("status")

        else:
            qs = qs.order_by("-created_at")

        return qs
        
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["agents"] = User.objects.filter(is_active=True).order_by("username")
        context["zones"] = Zone.objects.all().order_by("name")
        context["task_type_choices"] = Task.TASK_TYPE_CHOICES
        context["status_choices"] = Task.STATUS_CHOICES
        context["priority_choices"] = Task.PRIORITY_CHOICES

        return context

# -----------------------
# DETALLE
# -----------------------
class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/task_detail.html"
    context_object_name = "task"


    def get_queryset(self):

        user = self.request.user

        qs = Task.objects.select_related("assigned_to", "zone")

        # Admin y manager ven todo
        if user.is_superuser or user.role in ["admin", "manager"]:
            return qs

        # Agent solo ve sus tareas
        return qs.filter(assigned_to=user)
    

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["activities"] = (
            Activity.objects
            .filter(task=self.object)
            .select_related("user")
            .order_by("-created_at")[:20]
        )

        return context


# -----------------------
# CREAR TAREA (MANAGER / ADMIN)
# -----------------------
class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"
    success_url = reverse_lazy("task_list")

    def form_valid(self, form):

        form.instance.created_by = self.request.user

        response = super().form_valid(form)

        log_activity(
            self.request.user,
            "task_created",
            f"Creó la tarea '{self.object.title}'",
            task=self.object
        )

        return response


# -----------------------
# EDITAR TAREA
# -----------------------
class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"
    success_url = reverse_lazy("task_list")

    def form_valid(self, form):

        task = self.get_object()

        old_status = task.status
        old_priority = task.priority
        old_assigned = task.assigned_to

        response = super().form_valid(form)

        if old_status != self.object.status:
            new_status = self.object.status
            if new_status == "done":
                log_activity(
                    self.request.user,
                    "task_completed",
                    f"Completó la tarea '{task.title}'"
                )
            else:
                old_status_display = dict(Task.STATUS_CHOICES).get(old_status)
                new_status_display = self.object.get_status_display()
                log_activity(
                    self.request.user,
                    "task_status_changed",
                    f"Cambió el estado de '{self.object.title}' "
                    f"de '{old_status_display}' a '{new_status_display}'"
                )

        if old_priority != self.object.priority:

            old_priority_display = dict(Task.PRIORITY_CHOICES).get(old_priority)
            new_priority_display = self.object.get_priority_display()

            log_activity(
                self.request.user,
                "task_priority_changed",
                f"Cambió la prioridad de '{self.object.title}' de "
                f"{old_priority_display} a {new_priority_display}",
                contact=task.contact,
                task=task
            )

        if old_assigned != self.object.assigned_to:

            assigned_to_name = (
                self.object.assigned_to.username
                if self.object.assigned_to
                else "Sin asignar"
            )

            log_activity(
                self.request.user,
                "task_reassigned",
                f"Reasignó la tarea '{self.object.title}' a "
                f"{assigned_to_name}",
                contact=task.contact,
                task=task
            )

        return response

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser or user.role in ["admin", "manager"]:
            return Task.objects.all()

        # agentes solo pueden editar sus tareas
        return Task.objects.filter(assigned_to=user)


# -----------------------
# BORRAR TAREA (solo admin/manager)
# -----------------------
@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if not (
        request.user.is_superuser
        or request.user.role in ["admin", "manager"]
    ):
        return redirect("task_list")

    if request.method == "POST":
        title = task.title
        contact = task.contact
        task.delete()
        log_activity(
            request.user,
            "task_deleted",
            f"Eliminó la tarea '{title}'",
            contact=contact,
        )
                
        return redirect("task_list")

    return redirect("task_list")

# -----------------------
# cambiar estado (solo admin/manager)
# -----------------------
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@require_POST
@login_required
def task_update_status(request, pk):

    task = get_object_or_404(Task, pk=pk)

    if not (
        request.user.is_superuser
        or request.user.role in ["admin", "manager"]
        or task.assigned_to == request.user
    ):
        return JsonResponse({"success": False}, status=403)

    status = request.POST.get("status")
    old_status = task.status
    
    

    if status in dict(Task.STATUS_CHOICES):
        task.status = status
        task.save()
        if status == "done":
            task.completed_at = timezone.now()
            task.save()
            log_activity(
                request.user,
                "task_completed",
                f"Completó la tarea '{task.title}'",
                contact=task.contact,
                task=task
             )
        else:
            old_status_display = dict(Task.STATUS_CHOICES).get(old_status)
            new_status_display = dict(Task.STATUS_CHOICES).get(status)
            task.completed_at = None
            task.save()

            log_activity(
                request.user,
                "task_status_changed",
                f"Cambió el estado de '{task.title}' "
                f"de '{old_status_display}' a '{new_status_display}'",
                contact=task.contact,
                task=task
            )

        return JsonResponse({
            "success": True,
            "status": task.get_status_display()
        })

    return JsonResponse({"success": False}, status=400)


@require_POST
@login_required
def task_update_priority(request, pk):

    task = get_object_or_404(Task, pk=pk)
    old_priority = task.priority
    if not (
        request.user.is_superuser
        or request.user.role in ["admin", "manager"]
        or task.assigned_to == request.user
    ):
        return JsonResponse({"success": False}, status=403)

    priority = request.POST.get("priority")

    if priority in dict(Task.PRIORITY_CHOICES):
        task.priority = priority
        task.save()

        old_priority_display = dict(Task.PRIORITY_CHOICES).get(old_priority)
        new_priority_display = task.get_priority_display()

        log_activity(
            request.user,
            "task_priority_changed",
            f"Cambió la prioridad de la tarea '{task.title}' de '{old_priority_display}' a {new_priority_display}",
            contact=task.contact,
            task=task
        )

        return JsonResponse({
            "success": True,
            "priority": task.get_priority_display()
        })

    return JsonResponse({"success": False}, status=400)

