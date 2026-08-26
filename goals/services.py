from calendar_app.models import Appointment, ProposalAppointment
from contacts.models import Contact
from listings.models import Listing
from news.models import News
from orders.models import Order
from properties.models import Property
from sales.models import RentalContract, Sale
from django.db.models import Q


def _metric_queryset(goal, agent_ids):
    period = (goal.start_date, goal.end_date)

    if goal.metric == "listings":
        return Listing.objects.filter(
            agent_id__in=agent_ids,
            created_at__date__range=period,
        )
    if goal.metric == "orders":
        return Order.objects.filter(
            agent_id__in=agent_ids,
            created_at__date__range=period,
        )
    if goal.metric == "news":
        return News.objects.filter(
            agent_id__in=agent_ids,
            created_at__date__range=period,
        )
    if goal.metric in {
        "sale_appointments",
        "acquisition_appointments",
        "follow_up_appointments",
    }:
        appointment_type = {
            "sale_appointments": "sale",
            "acquisition_appointments": "acquisition",
            "follow_up_appointments": "follow_up",
        }[goal.metric]
        return Appointment.objects.filter(
            agent_id__in=agent_ids,
            appointment_type=appointment_type,
            date__range=period,
        ).exclude(status="cancelled")
    if goal.metric == "contacts":
        return Contact.objects.filter(
            assigned_agent_id__in=agent_ids,
            created_at__date__range=period,
        )
    if goal.metric in {
        "properties",
        "vacant_properties",
        "tenant_properties",
    }:
        queryset = Property.objects.filter(
            created_at__date__range=period,
        ).filter(
            Q(created_by_id__in=agent_ids)
            | Q(
                created_by__isnull=True,
                contacts__is_owner=True,
                contacts__assigned_agent_id__in=agent_ids,
            )
        )
        if goal.metric == "vacant_properties":
            queryset = queryset.filter(occupied_by="vacant")
        elif goal.metric == "tenant_properties":
            queryset = queryset.filter(occupied_by="tenants")
        return queryset
    if goal.metric == "proposals":
        return ProposalAppointment.objects.filter(
            agent_id__in=agent_ids,
            created_at__date__range=period,
        )
    if goal.metric == "sales":
        return Sale.objects.filter(
            agent_id__in=agent_ids,
            status="signed",
            sale_date__range=period,
        )
    if goal.metric == "rentals":
        return RentalContract.objects.filter(
            agent_id__in=agent_ids,
            status="signed",
            contract_date__range=period,
        )
    raise ValueError(f"Métrica de objetivo no soportada: {goal.metric}")


def calculate_progress(goal, agent_ids=None):
    if agent_ids is None:
        agent_ids = list(goal.assignees.values_list("id", flat=True))
    else:
        agent_ids = list(agent_ids)
    if not agent_ids:
        return 0
    return _metric_queryset(goal, agent_ids).distinct().count()


def build_goal_progress(goal, include_contributions=False):
    current = calculate_progress(goal)
    percentage = min(100, round(current * 100 / goal.target_count))
    data = {
        "goal": goal,
        "current": current,
        "remaining": max(goal.target_count - current, 0),
        "percentage": percentage,
        "is_achieved": current >= goal.target_count,
    }
    if include_contributions:
        data["contributions"] = [
            {
                "user": user,
                "current": calculate_progress(goal, [user.pk]),
            }
            for user in goal.assignees.all()
        ]
    return data
