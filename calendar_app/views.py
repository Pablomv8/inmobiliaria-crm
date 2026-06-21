from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse

from .models import Appointment, Call
from .forms import AppointmentForm, CallForm
from news.models import News
from contacts.models import Contact
from django.contrib.auth.decorators import login_required

from itertools import chain

def create_appointment(request, news_id):

    news = get_object_or_404(News, id=news_id)

    if request.method == "POST":

        form = AppointmentForm(request.POST)

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

def create_call(request, news_id):

    news = get_object_or_404(News, id=news_id)

    if request.method == "POST":

        form = CallForm(request.POST)

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
def calendar_view(request):

    return render(
        request,
        "calendar_app/calendar.html"
    )

@login_required
def calendar_events(request):

    events = []

    appointments = Appointment.objects.filter(
        agent=request.user
    )

    for appointment in appointments:

        events.append({
            "id": f"appointment-{appointment.id}",
            "title": (
                f"📅 "
                f"{appointment.get_appointment_type_display()}"
            ),
            "start": (
                f"{appointment.date}"
                f"T"
                f"{appointment.time}"
            ),
            "color": "#16a34a",
        })

    calls = Call.objects.filter(
        agent=request.user
    )

    for call in calls:

        events.append({
            "id": f"call-{call.id}",
            "title": (
                f"📞 "
                f"{call.contact.name}"
            ),
            "start": (
                f"{call.date}"
                f"T"
                f"{call.time}"
            ),
            "color": "#2563eb",
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