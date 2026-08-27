from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q


def can_manage_assignments(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.role in ["admin", "manager"])
    )


def can_manage_office(user):
    """Puede consultar y modificar registros de cualquier agente."""
    return can_manage_assignments(user)


def can_manage_object(user, obj, *assignment_fields):
    """Comprueba si el registro pertenece al usuario o gestiona la oficina."""
    if can_manage_office(user):
        return True
    if not user or not user.is_authenticated:
        return False

    for field_name in assignment_fields:
        assigned_id = getattr(obj, f"{field_name}_id", None)
        if assigned_id == user.pk:
            return True
    return False


def require_object_management(user, obj, *assignment_fields):
    if not can_manage_object(user, obj, *assignment_fields):
        raise PermissionDenied


def scope_to_user(queryset, user, assignment_field="agent"):
    """Managers ven todo; agentes únicamente su cartera asignada."""
    if can_manage_office(user):
        return queryset
    return queryset.filter(**{assignment_field: user})


def has_related_records(instance):
    """Indica si un borrado físico destruiría o desconectaría historial."""
    for relation in instance._meta.related_objects:
        accessor = relation.get_accessor_name()
        if not accessor:
            continue
        try:
            related = getattr(instance, accessor)
        except ObjectDoesNotExist:
            continue
        if relation.one_to_one:
            if related is not None:
                return True
        elif related.exists():
            return True
    return False


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
