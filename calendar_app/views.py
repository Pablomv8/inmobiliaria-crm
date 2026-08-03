from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.urls import reverse

from .models import Appointment, Call
from .forms import AppointmentForm, AppointmentResultForm, CallForm
from news.models import News
from contacts.models import Contact
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from collections import defaultdict


from datetime import date, timedelta
from itertools import chain, groupby
from users.models import User
from calendar_app.models import (
    Appointment,
    Call
)


@login_required
def create_appointment(request, news_id):

    news = get_object_or_404(News, id=news_id)

    if not news.comments.exists():

        messages.warning(
            request,
            (
                "Esta noticia no tiene comentarios registrados. "
                "Se recomienda documentar la conversación antes "
                "de programar una cita."
            )
        )

    if request.method == "POST":

        form = AppointmentForm(
            request.POST or None,
            user=request.user
        )

        if form.is_valid():

            appointment = form.save(commit=False)

            appointment.news = news
            appointment.contact = news.related_property.contacts.first()
            appointment.related_property = news.related_property
            appointment.agent = request.user

            appointment.save()

            return redirect("news_detail", news.id)

    else:

        form = AppointmentForm()

    return render(request, "appointments/form.html", {
        "form": form,
        "news": news
    })

@login_required
def create_call(request, news_id):

    news = get_object_or_404(News, id=news_id)

    if request.method == "POST":

        form = CallForm(
            request.POST or None,
            user=request.user
        )

        if form.is_valid():

            call = form.save(commit=False)

            call.news = news
            call.contact = news.related_property.contacts.first()
            call.agent = request.user

            call.save()

            return redirect("news_detail", news.id)

    else:

        form = CallForm()

    return render(request, "calls/form.html", {
        "form": form,
        "news": news
    })

@login_required
def appointment_detail(request, pk):

    appointment = get_object_or_404(
        Appointment.objects.select_related(
            "news",
            "related_property",
            "contact",
            "agent",
        ),
        pk=pk
    )

    listing = appointment.generated_listing.first()

    return render(
        request,
        "calendar_app/appointment_detail.html",
        {
            "appointment": appointment,
            "result_form": AppointmentResultForm(instance=appointment),
            "listing": listing,
        }
    )


@login_required
@require_POST
def add_appointment_result(request, pk):
    appointment = get_object_or_404(
        Appointment,
        pk=pk,
        agent=request.user,
    )
    form = AppointmentResultForm(request.POST, instance=appointment)

    if form.is_valid():
        appointment = form.save(commit=False)
        appointment.status = "completed"
        appointment.save(update_fields=["result_comment", "status"])
        messages.success(
            request,
            "Comentario guardado. Indica ahora si la cita tuvo éxito.",
        )
    else:
        listing = appointment.generated_listing.first()
        return render(
            request,
            "calendar_app/appointment_detail.html",
            {
                "appointment": appointment,
                "result_form": form,
                "listing": listing,
            },
            status=400,
        )

    return redirect("appointment_detail", pk=appointment.pk)


@login_required
@require_POST
def schedule_call_from_appointment(request, pk):
    appointment = get_object_or_404(
        Appointment,
        pk=pk,
        agent=request.user,
    )

    if (
        appointment.status != "completed"
        or not appointment.result_comment.strip()
    ):
        messages.warning(
            request,
            "Añade el comentario de resultado antes de programar la llamada.",
        )
        return redirect("appointment_detail", pk=appointment.pk)

    if appointment.news is None:
        messages.error(request, "La cita no tiene una noticia asociada.")
        return redirect("appointment_detail", pk=appointment.pk)

    appointment.result_success = False
    appointment.save(update_fields=["result_success"])

    return redirect("create_call", news_id=appointment.news_id)

@login_required
def call_detail(request, pk):

    call = get_object_or_404(
        Call,
        pk=pk
    )

    return render(
        request,
        "calendar_app/call_detail.html",
        {
            "call": call
        }
    )

@login_required
def update_appointment_status(request, appointment_id, status):

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        agent=request.user
    )

    if status in ["completed", "cancelled", "scheduled"]:

        appointment.status = status
        appointment.save()

    return redirect(
        "appointment_detail",
        appointment.id
    )

@login_required
def update_call_status(request, call_id, status):

    call = get_object_or_404(
        Call,
        id=call_id,
        agent=request.user
    )

    if status in ["completed", "cancelled", "pending"]:

        call.status = status
        call.save()

    return redirect(
        "call_detail",
        call.id
    )

@login_required
def calendar_view(request):

    today = date.today()
    tomorrow = today + timedelta(days=1)
    calls = Call.objects.filter(agent=request.user)
    appointments = Appointment.objects.filter(agent=request.user)
    today_calls = Call.objects.filter(
        agent=request.user,
        date=today
    )

    for item in today_calls:
        item.event_type = "call"

    today_appointments = Appointment.objects.filter(
        agent=request.user,
        date=today
    )

    for item in today_appointments:
        item.event_type = "appointment"

    today_events = sorted(
        chain(
            today_calls,
            today_appointments
        ),
        key=lambda x: x.time
    )

    tomorrow_calls = Call.objects.filter(
        agent=request.user,
        date=tomorrow
    )

    for item in tomorrow_calls:
        item.event_type = "call"

    tomorrow_appointments = Appointment.objects.filter(
        agent=request.user,
        date=tomorrow
    )

    for item in tomorrow_appointments:
        item.event_type = "appointment"

    tomorrow_events = sorted(
        chain(
            tomorrow_calls,
            tomorrow_appointments
        ),
        key=lambda x: x.time
    )
    agents = User.objects.filter(
        role="agent"
    )

    
    events = []

    for call in calls:
        if not call.date:
            continue

        events.append({
            "type": "call",
            "date": call.date,
            "time": call.time,
            "object": call
        })

    for appt in appointments:
        if not appt.date:
            continue

        events.append({
            "type": "appointment",
            "date": appt.date,
            "time": appt.time,
            "object": appt
        })

    # 🔥 ORDEN ÚNICO (IMPORTANTE)
    events = sorted(events, key=lambda e: (e["date"], e["time"]))

    # 🔥 GROUPBY CORRECTO
    agenda_by_day = [
        (day, list(group))
        for day, group in groupby(events, key=lambda e: e["date"])
    ]

    
    return render(
        request,
        "calendar_app/calendar.html",
        {
            "today_events": today_events,
            "tomorrow_events": tomorrow_events,
            "agents" : agents,
            "agenda_by_day" : agenda_by_day,
        }
    )

@login_required
def calendar_events(request):

    agent_ids = request.GET.getlist("agents")

    # BASE QUERYSET
    appointments = Appointment.objects.all()
    calls = Call.objects.all()

    # SI NO ES MANAGER → solo sus eventos
    if request.user.role not in ["admin", "manager"]:

        appointments = appointments.filter(agent=request.user)
        calls = calls.filter(agent=request.user)

    # SI ES MANAGER Y HAY FILTRO DE AGENTES
    elif agent_ids:

        appointments = appointments.filter(agent_id__in=agent_ids)
        calls = calls.filter(agent_id__in=agent_ids)
        print("AGENTS:", agent_ids)

        print(
            "APPOINTMENTS:",
            Appointment.objects.filter(
                agent_id__in=agent_ids
            ).count()
        )

        print(
            "CALLS:",
            Call.objects.filter(
                agent_id__in=agent_ids
            ).count()
        )


    events = []
    
    for appointment in appointments:

        events.append({
            "id": f"appointment-{appointment.id}",
            "title": (
                f"📅 Cita de {appointment.get_appointment_type_display()}\n"
                f"{appointment.related_property.full_address}"
            ),
            "start": (
                f"{appointment.date}"
                f"T"
                f"{appointment.time}"
            ),
            "color": "#16a34a",
            "url": reverse(
                "appointment_detail",
                args=[appointment.id]
            )
        })


    for call in calls:

        events.append({
            "id": f"call-{call.id}",
            "title": (
                f"📞 Llamada a "
                f"{call.contact.name}"
            ),
            "start": (
                f"{call.date}"
                f"T"
                f"{call.time}"
            ),
            "color": "#2563eb",
            "url": reverse(
                "call_detail",
                args=[call.id]
            )
        })

    return JsonResponse(
        events,
        safe=False
    )

@login_required
def agenda(request):

    appointments = Appointment.objects.filter(
        agent=request.user
    )

    calls = Call.objects.filter(
        agent=request.user
    )

    events = []

    for appointment in appointments:

        events.append({
            "type": "appointment",
            "date": appointment.date,
            "time": appointment.time,
            "object": appointment,
        })

    for call in calls:

        events.append({
            "type": "call",
            "date": call.date,
            "time": call.time,
            "object": call,
        })

    events.sort(
        key=lambda x: (
            x["date"],
            x["time"]
        )
    )

    return render(
        request,
        "calendar_app/agenda.html",
        {
            "events": events
        }
    )


@login_required
def available_slots(request):

    selected_date = request.GET.get("date")

    appointments = Appointment.objects.filter(
        agent=request.user,
        date=selected_date,
        status="scheduled"
    ).values_list(
        "time",
        flat=True
    )

    calls = Call.objects.filter(
        agent=request.user,
        date=selected_date,
        status="pending"
    ).values_list(
        "time",
        flat=True
    )

    occupied = [
        t.strftime("%H:%M")
        for t in chain(
            appointments,
            calls
        )
    ]

    return JsonResponse({
        "occupied": occupied
    })
