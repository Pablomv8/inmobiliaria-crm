from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.urls import reverse

from .models import Appointment, Call
from .forms import AppointmentForm, CallForm
from news.models import News
from contacts.models import Contact
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from datetime import date, timedelta
from itertools import chain
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
        Appointment,
        pk=pk
    )

    return render(
        request,
        "calendar_app/appointment_detail.html",
        {
            "appointment": appointment
        }
    )

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

    return render(
        request,
        "calendar_app/calendar.html",
        {
            "today_events": today_events,
            "tomorrow_events": tomorrow_events,
            "agents" : agents,
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

    calls = Call.objects.filter(
        agent=request.user
    )

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