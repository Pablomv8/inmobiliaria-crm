from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.urls import reverse
from django.utils import timezone

from calendar_app.models import Appointment, Call
from tasks.models import Task


@dataclass
class DailyItem:
    key: str
    kind: str
    title: str
    description: str
    time_label: str
    url: str
    action_label: str
    starts_at: datetime
    icon: str
    tone: str
    is_past: bool = False


def _aware_at(day, at_time=time.min):
    return timezone.make_aware(
        datetime.combine(day, at_time),
        timezone.get_current_timezone(),
    )


def _task_is_overdue(task, now, today):
    if task.task_type == "custom":
        return bool(task.due_date and task.due_date < now)
    end_date = task.schedule_end_date
    if end_date is None:
        return False
    if end_date < today:
        return True
    return bool(
        end_date == today
        and task.end_time
        and task.end_time < timezone.localtime(now).time()
    )


def _task_deadline(task):
    if task.task_type == "custom":
        return task.due_date
    return _aware_at(task.schedule_end_date, task.end_time or time.max)


def _task_occurs_today(task, today):
    if task.task_type == "custom":
        return bool(
            task.due_date
            and timezone.localtime(task.due_date).date() == today
        )
    return bool(
        task.schedule_date
        and task.schedule_end_date
        and task.schedule_date <= today <= task.schedule_end_date
    )


def build_daily_work(user, alerts, now=None):
    now = now or timezone.now()
    today = timezone.localdate(now)
    timeline = []

    appointments = Appointment.objects.filter(
        agent=user,
        date=today,
        status="scheduled",
    ).select_related("contact", "related_property")
    for appointment in appointments:
        starts_at = _aware_at(today, appointment.time)
        if appointment.related_property:
            description = f"{appointment.contact} · {appointment.related_property}"
        elif appointment.financial_entity:
            description = f"{appointment.contact} · {appointment.financial_entity}"
        else:
            description = str(appointment.contact)
        timeline.append(DailyItem(
            key=f"appointment-{appointment.pk}",
            kind="appointment",
            title=f"Cita de {appointment.get_appointment_type_display().lower()}",
            description=description,
            time_label=f"{appointment.time:%H:%M}–{appointment.end_time:%H:%M}",
            url=reverse("appointment_detail", args=[appointment.pk]),
            action_label="Registrar resultado",
            starts_at=starts_at,
            icon="fa-regular fa-calendar-check",
            tone="indigo",
            is_past=starts_at < now,
        ))

    calls = Call.objects.filter(
        agent=user,
        date=today,
        status="pending",
    ).select_related("contact")
    for call in calls:
        starts_at = _aware_at(today, call.time)
        timeline.append(DailyItem(
            key=f"call-{call.pk}",
            kind="call",
            title="Llamada de seguimiento",
            description=str(call.contact),
            time_label=f"{call.time:%H:%M}",
            url=reverse("call_detail", args=[call.pk]),
            action_label="Añadir resultado",
            starts_at=starts_at,
            icon="fa-solid fa-phone",
            tone="blue",
            is_past=starts_at < now,
        ))

    active_tasks = list(
        Task.objects.filter(
            assigned_to=user,
            status__in=["pending", "in_progress"],
        ).select_related("zone", "contact")
    )
    overdue_tasks = sorted(
        [task for task in active_tasks if _task_is_overdue(task, now, today)],
        key=_task_deadline,
    )
    for task in active_tasks:
        if task in overdue_tasks or not _task_occurs_today(task, today):
            continue
        if task.task_type == "custom":
            starts_at = task.due_date
            time_label = timezone.localtime(task.due_date).strftime("%H:%M")
            description = task.description
        else:
            starts_at = _aware_at(today, task.start_time)
            time_label = f"{task.start_time:%H:%M}–{task.end_time:%H:%M}"
            if task.task_type == "zone_sweep":
                description = f"Zona {task.zone}" if task.zone else "Zona sin asignar"
            else:
                description = "Ruta de calles seleccionada"
        timeline.append(DailyItem(
            key=f"task-{task.pk}",
            kind="task",
            title=task.title,
            description=description,
            time_label=time_label,
            url=reverse("task_detail", args=[task.pk]),
            action_label="Abrir tarea",
            starts_at=starts_at,
            icon=(
                "fa-solid fa-route"
                if task.task_type == "street_sweep"
                else "fa-solid fa-map-location-dot"
                if task.task_type == "zone_sweep"
                else "fa-regular fa-clipboard"
            ),
            tone="emerald" if task.task_type != "custom" else "violet",
            is_past=starts_at < now,
        ))

    timeline.sort(key=lambda item: (item.starts_at, item.kind, item.title))
    decisions = [item for item in alerts if item.category == "workflow"]
    follow_ups = [
        item for item in alerts
        if item.category in {"inactivity", "expirations"}
    ][:8]
    completed_today = (
        Appointment.objects.filter(agent=user, date=today, status="completed").count()
        + Call.objects.filter(agent=user, date=today, status="completed").count()
        + Task.objects.filter(
            assigned_to=user,
            status="done",
            completed_at__date=today,
        ).count()
    )
    return {
        "today": today,
        "timeline": timeline,
        "overdue_tasks": overdue_tasks,
        "decisions": decisions,
        "follow_ups": follow_ups,
        "pending_today": len(timeline),
        "completed_today": completed_today,
        "overdue_count": len(overdue_tasks),
        "decision_count": len(decisions),
    }
