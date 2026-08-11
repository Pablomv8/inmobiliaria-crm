from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import Appointment, Call


def aware_datetime(day, value):
    result = datetime.combine(day, value)
    return timezone.make_aware(result, timezone.get_current_timezone())


def intervals_overlap(first_start, first_end, second_start, second_end):
    return first_start < second_end and second_start < first_end


def occupied_intervals(agent, selected_date, exclude_appointment_id=None):
    from tasks.models import Task
    from tasks.scheduling import ACTIVE_TASK_STATUSES, task_occurrences

    appointments = Appointment.objects.filter(
        agent=agent,
        date=selected_date,
        status="scheduled",
    ).exclude(pk=exclude_appointment_id)
    calls = Call.objects.filter(
        agent=agent,
        date=selected_date,
        status="pending",
    )
    tasks = Task.objects.filter(
        assigned_to=agent,
        status__in=ACTIVE_TASK_STATUSES,
    ).select_related("zone")

    intervals = []
    for appointment in appointments:
        intervals.append({
            "start": aware_datetime(appointment.date, appointment.time),
            "end": aware_datetime(appointment.date, appointment.end_time),
            "type": "appointment",
            "label": f"Cita de {appointment.get_appointment_type_display()}",
        })
    for call in calls:
        start = aware_datetime(call.date, call.time)
        intervals.append({
            "start": start,
            "end": start + timedelta(minutes=30),
            "type": "call",
            "label": "Llamada",
        })
    for task in tasks:
        for start, end in task_occurrences(task):
            if start.date() == selected_date:
                intervals.append({
                    "start": start,
                    "end": end,
                    "type": "task",
                    "label": task.title,
                })

    return sorted(intervals, key=lambda item: item["start"])


def schedule_has_conflict(
    agent,
    selected_date,
    start_time,
    end_time,
    exclude_appointment_id=None,
):
    if not all([agent, selected_date, start_time, end_time]):
        return False

    start = aware_datetime(selected_date, start_time)
    end = aware_datetime(selected_date, end_time)
    return any(
        intervals_overlap(start, end, item["start"], item["end"])
        for item in occupied_intervals(
            agent,
            selected_date,
            exclude_appointment_id=exclude_appointment_id,
        )
    )


def slot_has_conflict(agent, selected_date, start_time, minutes=30):
    if not all([agent, selected_date, start_time]):
        return False

    start = aware_datetime(selected_date, start_time)
    end = start + timedelta(minutes=minutes)
    return any(
        intervals_overlap(start, end, item["start"], item["end"])
        for item in occupied_intervals(agent, selected_date)
    )


def occupied_half_hour_slots(agent, selected_date, exclude_appointment_id=None):
    intervals = occupied_intervals(
        agent,
        selected_date,
        exclude_appointment_id=exclude_appointment_id,
    )
    occupied = set()
    slot_start = aware_datetime(selected_date, time(6, 0))
    for offset in range(28):
        start = slot_start + timedelta(minutes=30 * offset)
        end = start + timedelta(minutes=30)
        if any(
            intervals_overlap(start, end, item["start"], item["end"])
            for item in intervals
        ):
            occupied.add(start.strftime("%H:%M"))
    return occupied
