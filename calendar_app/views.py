from django.shortcuts import render, get_object_or_404, redirect

from news.models import News
from .models import Appointment, Call


def appointment_create(request, news_id, type):

    news = get_object_or_404(News, id=news_id)

    if request.method == "POST":

        Appointment.objects.create(
            news=news,
            agent=request.user,
            type=type,
            date=request.POST.get("date"),
            time=request.POST.get("time"),
        )

        return redirect("news_detail", news.id)

    return render(request, "calendar/create.html", {
        "news": news,
        "type": type
    })