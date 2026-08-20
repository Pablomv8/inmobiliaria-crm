from django.contrib.auth import get_user_model
from django.db.models import Q


def can_manage_assignments(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.role in ["admin", "manager"])
    )


def assignable_agents(current_agent=None):
    assignable_roles = ["agent", "manager", "admin"]
    queryset = get_user_model().objects.filter(
        is_active=True,
        role__in=assignable_roles,
    )
    if current_agent is not None and current_agent.pk:
        queryset = get_user_model().objects.filter(
            Q(is_active=True, role__in=assignable_roles)
            | Q(pk=current_agent.pk)
        )
    return queryset.distinct().order_by("first_name", "last_name", "username")
