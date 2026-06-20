from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404

from .forms import NewsForm, NewsCommentForm

from .models import News

from properties.models import Property

from itertools import chain
from operator import attrgetter

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
        return "call"

    if isinstance(obj, Appointment):
        return "appointment"

    return "comment"

def news_detail(request, pk):

    news = get_object_or_404(
        News,
        pk=pk
    )
    comments = news.comments.all().order_by("-created_at")

    form = NewsCommentForm()

    appointments = Appointment.objects.filter(news=news)
    calls = Call.objects.filter(news=news)

    activities = sorted(
        chain(appointments, calls, comments),
        key=lambda x: x.created_at,
        reverse=True
    )


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