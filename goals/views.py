from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from config.pagination import paginate
from users.models import User

from .forms import GoalForm
from .models import Goal
from .services import build_goal_progress


def can_manage_goals(user):
    return user.is_superuser or user.role in ["admin", "manager"]


def visible_goals(user):
    queryset = Goal.objects.select_related("created_by").prefetch_related(
        "assignees"
    )
    if can_manage_goals(user):
        return queryset
    return queryset.filter(assignees=user)


@login_required
def goal_list(request):
    queryset = visible_goals(request.user)
    search = request.GET.get("search", "").strip()
    metric = request.GET.get("metric", "")
    scope = request.GET.get("scope", "")
    agent = request.GET.get("agent", "")
    period_status = request.GET.get("status", "")

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )
    if metric in dict(Goal.METRIC_CHOICES):
        queryset = queryset.filter(metric=metric)
    if scope in dict(Goal.SCOPE_CHOICES):
        queryset = queryset.filter(scope=scope)
    if agent and can_manage_goals(request.user):
        queryset = queryset.filter(assignees__id=agent)

    queryset = queryset.distinct()
    rows = [
        build_goal_progress(
            goal,
            include_contributions=(
                goal.scope == Goal.SCOPE_TEAM and can_manage_goals(request.user)
            ),
        )
        for goal in queryset
    ]
    if period_status in {"upcoming", "active", "finished", "achieved"}:
        rows = [
            row
            for row in rows
            if (
                row["is_achieved"]
                if period_status == "achieved"
                else row["goal"].period_status == period_status
                and not row["is_achieved"]
            )
        ]

    page_obj = paginate(request, rows, per_page=12)
    context = {
        "goal_rows": page_obj,
        "page_obj": page_obj,
        "can_manage_goals": can_manage_goals(request.user),
        "metric_choices": Goal.METRIC_CHOICES,
        "scope_choices": Goal.SCOPE_CHOICES,
        "agents": User.objects.filter(is_active=True, role="agent").order_by(
            "first_name", "last_name", "username"
        ),
    }
    return render(request, "goals/list.html", context)


@login_required
def goal_detail(request, pk):
    goal = get_object_or_404(visible_goals(request.user), pk=pk)
    progress = build_goal_progress(goal, include_contributions=True)
    return render(
        request,
        "goals/detail.html",
        {
            **progress,
            "can_manage_goals": can_manage_goals(request.user),
        },
    )


@login_required
def goal_create(request):
    if not can_manage_goals(request.user):
        raise PermissionDenied
    form = GoalForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        goal = form.save(commit=False)
        goal.created_by = request.user
        goal.save()
        form.save_m2m()
        messages.success(request, "El objetivo se ha creado correctamente.")
        return redirect("goal_detail", pk=goal.pk)
    return render(request, "goals/form.html", {"form": form})


@login_required
def goal_update(request, pk):
    if not can_manage_goals(request.user):
        raise PermissionDenied
    goal = get_object_or_404(Goal, pk=pk)
    form = GoalForm(request.POST or None, instance=goal)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "El objetivo se ha actualizado correctamente.")
        return redirect("goal_detail", pk=goal.pk)
    return render(request, "goals/form.html", {"form": form, "object": goal})


@login_required
def goal_delete(request, pk):
    if not can_manage_goals(request.user):
        raise PermissionDenied
    goal = get_object_or_404(Goal, pk=pk)
    if request.method == "POST":
        goal.delete()
        messages.success(request, "El objetivo se ha eliminado.")
        return redirect("goal_list")
    return render(request, "goals/delete.html", {"goal": goal})
