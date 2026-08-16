from datetime import datetime, time, timedelta

from django.utils import timezone


ACTIVE_TASK_STATUSES = ["pending", "in_progress"]


def _aware_datetime(day, value):
    result = datetime.combine(day, value)
    return timezone.make_aware(result, timezone.get_current_timezone())


def build_occurrences(
    task_type,
    due_date=None,
    schedule_date=None,
    start_time=None,
    end_time=None,
    repeat_days=None,
):
    if task_type == "custom" and due_date:
        start = timezone.localtime(due_date) if timezone.is_aware(due_date) else due_date
        if timezone.is_naive(start):
            start = timezone.make_aware(start, timezone.get_current_timezone())
        return [(start, start + timedelta(hours=1))]

    if (
        task_type == "zone_sweep"
        and schedule_date
        and start_time
        and end_time
        and repeat_days
        and end_time > start_time
    ):
        return [
            (
                _aware_datetime(schedule_date + timedelta(days=offset), start_time),
                _aware_datetime(schedule_date + timedelta(days=offset), end_time),
            )
            for offset in range(repeat_days)
        ]

    return []


def task_occurrences(task):
    return build_occurrences(
        task.task_type,
        due_date=task.due_date,
        schedule_date=task.schedule_date,
        start_time=task.start_time,
        end_time=task.end_time,
        repeat_days=task.repeat_days,
    )


def intervals_overlap(first_start, first_end, second_start, second_end):
    return first_start < second_end and second_start < first_end


def schedule_has_conflict(assigned_to, occurrences, exclude_task_id=None):
    if assigned_to is None or not occurrences:
        return False

    from calendar_app.models import Appointment, Call
    from tasks.models import Task

    first_day = min(start.date() for start, _ in occurrences)
    last_day = max(start.date() for start, _ in occurrences)

    appointments = Appointment.objects.filter(
        agent=assigned_to,
        status="scheduled",
        date__range=[first_day, last_day],
    )
    calls = Call.objects.filter(
        agent=assigned_to,
        status="pending",
        date__range=[first_day, last_day],
    )
    tasks = Task.objects.filter(
        assigned_to=assigned_to,
        status__in=ACTIVE_TASK_STATUSES,
    ).exclude(pk=exclude_task_id)

    occupied_intervals = []
    for appointment in appointments:
        start = _aware_datetime(appointment.date, appointment.time)
        end = _aware_datetime(appointment.date, appointment.end_time)
        occupied_intervals.append((start, end))
    for call in calls:
        start = _aware_datetime(call.date, call.time)
        occupied_intervals.append((start, start + timedelta(minutes=30)))
    for task in tasks:
        occupied_intervals.extend(task_occurrences(task))

    return any(
        intervals_overlap(start, end, occupied_start, occupied_end)
        for start, end in occurrences
        for occupied_start, occupied_end in occupied_intervals
    )


def task_has_conflict_with_slot(agent, selected_date, selected_time):
    if agent is None or selected_date is None or selected_time is None:
        return False

    from tasks.models import Task

    slot_start = _aware_datetime(selected_date, selected_time)
    slot_end = slot_start + timedelta(minutes=30)
    tasks = Task.objects.filter(
        assigned_to=agent,
        status__in=ACTIVE_TASK_STATUSES,
    )
    return any(
        intervals_overlap(slot_start, slot_end, task_start, task_end)
        for task in tasks
        for task_start, task_end in task_occurrences(task)
    )


def occupied_task_slots(agent, selected_date):
    from tasks.models import Task

    tasks = Task.objects.filter(
        assigned_to=agent,
        status__in=ACTIVE_TASK_STATUSES,
    )
    task_intervals = [
        (start, end)
        for task in tasks
        for start, end in task_occurrences(task)
        if start.date().isoformat() == str(selected_date)
    ]

    occupied = set()
    slot_start = _aware_datetime(
        datetime.strptime(str(selected_date), "%Y-%m-%d").date(),
        time(6, 0),
    )
    for offset in range(28):
        start = slot_start + timedelta(minutes=30 * offset)
        end = start + timedelta(minutes=30)
        if any(
            intervals_overlap(start, end, task_start, task_end)
            for task_start, task_end in task_intervals
        ):
            occupied.add(start.strftime("%H:%M"))
    return occupied
