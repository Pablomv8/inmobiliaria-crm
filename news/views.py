from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404

from .forms import NewsForm, NewsCommentForm

from .models import News

from properties.models import Property

from itertools import chain
from operator import attrgetter

from datetime import datetime
from django.utils import timezone

from calendar_app.models import Appointment, Call
from .models import NewsComment


def news_create(request, property_id):

    property_obj = get_object_or_404(
        Property,
        pk=property_id
    )

    if request.method == "POST":

        form = NewsForm(request.POST)

        if form.is_valid():

            news = form.save(
                commit=False
            )

            news.related_property = property_obj

            news.agent = request.user

            news.save()

            return redirect(
                "news_detail",
                news.id
            )

    else:

        form = NewsForm()

    return render(
        request,
        "news/create.html",
        {
            "form": form,
            "property": property_obj,
        }
    )


####Para obtener si es llamada,cita o comentario
def get_activity_type(obj):

    if isinstance(obj, Call):
        return "Call"

    if isinstance(obj, Appointment):
        return "Appointment"

    return "Comment"

def news_detail(request, pk):

    news = get_object_or_404(
        News,
        pk=pk
    )
    comments = news.comments.all().order_by("-created_at")

    timeline = []
    # Comentarios
    for comment in news.comments.all():

        timeline.append({
            "type": "comment",
            "date": comment.created_at,
            "object": comment
        })

    # Llamadas
    for call in news.calls.all():

        timeline.append({
            "type": "call",
            "date": timezone.make_aware(
                datetime.combine(
                    call.date,
                    call.time
                )
            ),
            "object": call
        })

    # Citas
    for appointment in news.appointments.all():

        timeline.append({
            "type": "appointment",
            "date": timezone.make_aware(
                datetime.combine(
                    appointment.date,
                    appointment.time
                )
            ),
            "object": appointment
        })

    timeline.sort(
        key=lambda x: x["date"],
        reverse=True
    )

    form = NewsCommentForm()

    appointments = Appointment.objects.filter(news=news)
    calls = Call.objects.filter(news=news)

    activities = sorted(
        chain(appointments, calls, comments),
        key=lambda x: x.created_at,
        reverse=True
    )

    has_comments = news.comments.exists()


    for a in activities:
        a.activity_type = get_activity_type(a)

    return render(
        request,
        "news/detail.html",
        {
            "news": news,
            "comments": comments,
            "form": form,
            "appointments": appointments,
            "calls": calls,
            "activities": activities,
            "has_comments": has_comments,
            "timeline": timeline,
        }
    )

def news_add_comment(request, pk):

    news = get_object_or_404(
        News,
        pk=pk
    )

    if request.method == "POST":

        form = NewsCommentForm(
            request.POST
        )

        if form.is_valid():

            comment = form.save(
                commit=False
            )

            comment.news = news

            comment.user = request.user

            comment.save()

    return redirect(
        "news_detail",
        news.id
    )