from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.db.models import Max, Q
from django.urls import reverse
from django.utils import timezone

from calendar_app.models import Appointment, Call, ProposalAppointment
from listings.models import Listing
from news.models import News
from orders.models import Order
from properties.models import Property
from tasks.models import Task
from users.permissions import can_manage_office


ALERT_CATEGORIES = {
    "schedule": "Agenda",
    "tasks": "Tareas",
    "expirations": "Vencimientos",
    "inactivity": "Sin actividad",
    "workflow": "Decisiones pendientes",
}
ALERT_PRIORITIES = {
    "high": "Alta",
    "medium": "Media",
    "low": "Informativa",
}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class AlertItem:
    key: str
    category: str
    priority: str
    title: str
    description: str
    due_label: str
    url: str
    sort_at: datetime
    agent_id: int | None = None
    agent_name: str = "Sin asignar"
    icon: str = "fa-solid fa-bell"

    @property
    def category_label(self):
        return ALERT_CATEGORIES[self.category]

    @property
    def priority_label(self):
        return ALERT_PRIORITIES[self.priority]


def _user_name(user):
    if user is None:
        return "Sin asignar"
    return user.get_full_name() or user.username


def _aware_at(day, at_time=time.min):
    value = datetime.combine(day, at_time)
    return timezone.make_aware(value, timezone.get_current_timezone())


def _scoped(queryset, user, field):
    if can_manage_office(user):
        return queryset
    return queryset.filter(**{field: user})


def _property_scope(queryset, user):
    if can_manage_office(user):
        return queryset
    return queryset.filter(
        Q(assigned_agent=user)
        | Q(assigned_agent__isnull=True, created_by=user)
    )


def _add_schedule_alerts(alerts, user, now, today):
    appointment_limit = today + timedelta(days=2)
    appointments = _scoped(
        Appointment.objects.filter(
            status="scheduled",
            date__lte=appointment_limit,
        ).select_related("agent", "contact", "related_property"),
        user,
        "agent",
    )
    for appointment in appointments:
        starts_at = _aware_at(appointment.date, appointment.time)
        if starts_at < now:
            priority = "high"
            title = "Cita vencida sin completar"
            due_label = f"Venció el {appointment.date:%d/%m} a las {appointment.time:%H:%M}"
        else:
            priority = "medium"
            title = "Cita próxima"
            if appointment.date == today:
                due_label = f"Hoy a las {appointment.time:%H:%M}"
            elif appointment.date == today + timedelta(days=1):
                due_label = f"Mañana a las {appointment.time:%H:%M}"
            else:
                due_label = f"{appointment.date:%d/%m} a las {appointment.time:%H:%M}"
        alerts.append(AlertItem(
            key=f"appointment-{appointment.pk}",
            category="schedule",
            priority=priority,
            title=title,
            description=(
                f"{appointment.get_appointment_type_display()} con "
                f"{appointment.contact}."
            ),
            due_label=due_label,
            url=reverse("appointment_detail", args=[appointment.pk]),
            sort_at=starts_at,
            agent_id=appointment.agent_id,
            agent_name=_user_name(appointment.agent),
            icon="fa-regular fa-calendar-check",
        ))

    calls = _scoped(
        Call.objects.filter(
            status="pending",
            date__lte=appointment_limit,
        ).select_related("agent", "contact"),
        user,
        "agent",
    )
    for call in calls:
        starts_at = _aware_at(call.date, call.time)
        if starts_at < now:
            priority = "high"
            title = "Llamada vencida"
            due_label = f"Venció el {call.date:%d/%m} a las {call.time:%H:%M}"
        else:
            priority = "medium"
            title = "Llamada próxima"
            if call.date == today:
                due_label = f"Hoy a las {call.time:%H:%M}"
            elif call.date == today + timedelta(days=1):
                due_label = f"Mañana a las {call.time:%H:%M}"
            else:
                due_label = f"{call.date:%d/%m} a las {call.time:%H:%M}"
        alerts.append(AlertItem(
            key=f"call-{call.pk}",
            category="schedule",
            priority=priority,
            title=title,
            description=f"Llamada pendiente con {call.contact}.",
            due_label=due_label,
            url=reverse("call_detail", args=[call.pk]),
            sort_at=starts_at,
            agent_id=call.agent_id,
            agent_name=_user_name(call.agent),
            icon="fa-solid fa-phone",
        ))


def _add_task_alerts(alerts, user, now, today):
    tasks = _scoped(
        Task.objects.filter(status__in=["pending", "in_progress"]).select_related(
            "assigned_to",
            "zone",
        ),
        user,
        "assigned_to",
    )
    for task in tasks:
        overdue_at = None
        if task.task_type == "custom" and task.due_date and task.due_date < now:
            overdue_at = task.due_date
        elif (
            task.task_type in {"zone_sweep", "street_sweep"}
            and task.schedule_end_date
            and task.schedule_end_date < today
        ):
            overdue_at = _aware_at(task.schedule_end_date, task.end_time or time.max)
        if overdue_at is None:
            continue
        alerts.append(AlertItem(
            key=f"task-{task.pk}",
            category="tasks",
            priority="high",
            title="Tarea vencida",
            description=task.title,
            due_label=f"Pendiente desde {timezone.localtime(overdue_at):%d/%m/%Y}",
            url=reverse("task_detail", args=[task.pk]),
            sort_at=overdue_at,
            agent_id=task.assigned_to_id,
            agent_name=_user_name(task.assigned_to),
            icon="fa-regular fa-clipboard",
        ))


def _add_expiration_alerts(alerts, user, now, today):
    listing_limit = today + timedelta(days=7)
    listings = _scoped(
        Listing.objects.filter(
            status="active",
            end_date__isnull=False,
            end_date__lte=listing_limit,
        ).select_related("agent", "property", "owner"),
        user,
        "agent",
    )
    for listing in listings:
        expired = listing.end_date < today
        alerts.append(AlertItem(
            key=f"listing-expiration-{listing.pk}",
            category="expirations",
            priority="high" if expired else "medium",
            title="Encargo vencido" if expired else "Encargo próximo a vencer",
            description=f"{listing.property} · {listing.owner or 'Sin propietario'}.",
            due_label=(
                f"Venció el {listing.end_date:%d/%m/%Y}"
                if expired
                else f"Vence el {listing.end_date:%d/%m/%Y}"
            ),
            url=reverse("listing_detail", args=[listing.pk]),
            sort_at=_aware_at(listing.end_date),
            agent_id=listing.agent_id,
            agent_name=_user_name(listing.agent),
            icon="fa-solid fa-file-signature",
        ))

    proposal_limit = today + timedelta(days=3)
    proposals = _scoped(
        ProposalAppointment.objects.filter(
            status__in=["submitted", "acceptance_appointment", "counteroffer"],
            end_date__lte=proposal_limit,
        ).select_related("agent", "buyer", "listing__property"),
        user,
        "agent",
    )
    for proposal in proposals:
        expired = proposal.end_date < today
        alerts.append(AlertItem(
            key=f"proposal-expiration-{proposal.pk}",
            category="expirations",
            priority="high" if expired else "medium",
            title="Propuesta vencida" if expired else "Propuesta próxima a vencer",
            description=f"Oferta de {proposal.buyer} para {proposal.listing.property}.",
            due_label=(
                f"Venció el {proposal.end_date:%d/%m/%Y}"
                if expired
                else f"Vence el {proposal.end_date:%d/%m/%Y}"
            ),
            url=reverse("proposal_appointment_detail", args=[proposal.pk]),
            sort_at=_aware_at(proposal.end_date),
            agent_id=proposal.agent_id,
            agent_name=_user_name(proposal.agent),
            icon="fa-solid fa-hand-holding-dollar",
        ))


def _add_inactivity_alerts(alerts, user, now, today):
    threshold = now - timedelta(days=30)
    properties = _property_scope(
        Property.objects.filter(is_archived=False).annotate(
            last_comment=Max("comments__created_at"),
        ).filter(
            Q(status="contacted_30")
            | Q(status="never_contacted", created_at__lte=threshold)
            | Q(status="contacted", last_comment__lt=threshold)
        ).select_related(
            "assigned_agent",
            "created_by",
        ).distinct(),
        user,
    )
    for property_obj in properties:
        owner = property_obj.assigned_agent or property_obj.created_by
        last_activity = property_obj.last_comment or property_obj.created_at
        alerts.append(AlertItem(
            key=f"property-inactivity-{property_obj.pk}",
            category="inactivity",
            priority="medium",
            title="Inmueble sin contacto reciente",
            description=property_obj.full_address,
            due_label=f"Último contacto: {last_activity:%d/%m/%Y}",
            url=reverse("property_detail", args=[property_obj.pk]),
            sort_at=last_activity,
            agent_id=owner.pk if owner else None,
            agent_name=_user_name(owner),
            icon="fa-regular fa-building",
        ))

    news_items = _scoped(
        News.objects.exclude(status="closed").annotate(
            last_comment=Max("comments__created_at"),
            last_appointment=Max("appointments__created_at"),
            last_call=Max("calls__created_at"),
        ).select_related("agent", "related_property"),
        user,
        "agent",
    )
    for news_item in news_items:
        last_activity = max(
            value for value in [
                news_item.created_at,
                news_item.last_comment,
                news_item.last_appointment,
                news_item.last_call,
            ] if value is not None
        )
        if last_activity >= threshold:
            continue
        alerts.append(AlertItem(
            key=f"news-inactivity-{news_item.pk}",
            category="inactivity",
            priority="medium",
            title="Noticia sin actividad durante 30 días",
            description=str(news_item.related_property),
            due_label=f"Última actividad: {last_activity:%d/%m/%Y}",
            url=reverse("news_detail", args=[news_item.pk]),
            sort_at=last_activity,
            agent_id=news_item.agent_id,
            agent_name=_user_name(news_item.agent),
            icon="fa-regular fa-newspaper",
        ))

    orders = _scoped(
        Order.objects.exclude(status__in=["closed", "cancelled"]).annotate(
            last_comment=Max("comments__created_at"),
            last_appointment=Max("sale_appointments__created_at"),
        ).select_related("agent", "buyer"),
        user,
        "agent",
    )
    for order in orders:
        last_activity = max(
            value for value in [
                order.created_at,
                order.updated_at,
                order.last_comment,
                order.last_appointment,
            ] if value is not None
        )
        if last_activity >= threshold:
            continue
        alerts.append(AlertItem(
            key=f"order-inactivity-{order.pk}",
            category="inactivity",
            priority="medium",
            title="Pedido sin actividad durante 30 días",
            description=f"Pedido de {order.buyer}.",
            due_label=f"Última actividad: {last_activity:%d/%m/%Y}",
            url=reverse("order_detail", args=[order.pk]),
            sort_at=last_activity,
            agent_id=order.agent_id,
            agent_name=_user_name(order.agent),
            icon="fa-solid fa-cart-shopping",
        ))


def _add_workflow_alerts(alerts, user, now):
    appointments = _scoped(
        Appointment.objects.filter(status="completed").filter(
            Q(appointment_type__in=["acquisition", "sale"], result_success__isnull=True)
            | Q(appointment_type="proposal", proposal__isnull=True)
        ).select_related("agent", "contact"),
        user,
        "agent",
    )
    for appointment in appointments:
        if appointment.appointment_type == "acquisition":
            title = "Decidir resultado de adquisición"
            description = "Indica si se crea un encargo o se programa una llamada."
        elif appointment.appointment_type == "sale":
            title = "Decidir resultado de la visita"
            description = "Indica si el comprador quiere presentar una propuesta."
        else:
            title = "Registrar propuesta económica"
            description = "La cita terminó, pero todavía no se ha creado la propuesta."
        alerts.append(AlertItem(
            key=f"workflow-appointment-{appointment.pk}",
            category="workflow",
            priority="high",
            title=title,
            description=f"{appointment.contact}. {description}",
            due_label=f"Pendiente desde {appointment.date:%d/%m/%Y}",
            url=reverse("appointment_detail", args=[appointment.pk]),
            sort_at=_aware_at(appointment.date, appointment.end_time),
            agent_id=appointment.agent_id,
            agent_name=_user_name(appointment.agent),
            icon="fa-solid fa-circle-question",
        ))


def build_alerts(user):
    if not user or not user.is_authenticated:
        return []
    now = timezone.now()
    today = timezone.localdate()
    alerts = []
    _add_schedule_alerts(alerts, user, now, today)
    _add_task_alerts(alerts, user, now, today)
    _add_expiration_alerts(alerts, user, now, today)
    _add_inactivity_alerts(alerts, user, now, today)
    _add_workflow_alerts(alerts, user, now)
    return sorted(
        alerts,
        key=lambda item: (PRIORITY_ORDER[item.priority], item.sort_at, item.title),
    )


def summarize_alerts(alerts):
    return {
        "total": len(alerts),
        "high": sum(item.priority == "high" for item in alerts),
        "medium": sum(item.priority == "medium" for item in alerts),
        "low": sum(item.priority == "low" for item in alerts),
        "categories": {
            key: sum(item.category == key for item in alerts)
            for key in ALERT_CATEGORIES
        },
    }
