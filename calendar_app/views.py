from django.shortcuts import get_object_or_404, redirect, render

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