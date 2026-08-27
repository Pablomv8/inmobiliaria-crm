from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from calendar_app.models import Appointment, Call
from properties.models import Property
from users.models import User
from config.pagination import paginate
from users.permissions import can_manage_office, has_related_records, scope_to_user
from django.contrib import messages

from .forms import NewsCommentForm, NewsForm
from .models import News


@login_required
def news_list(request):
    news_items = News.objects.select_related(
        "related_property",
        "agent",
    )

    search = request.GET.get("search", "").strip()
    motivation = request.GET.get("motivation", "")
    status = request.GET.get("status", "")
    agent = request.GET.get("agent", "")
    ordering = request.GET.get("ordering", "recent")
    open_only = request.GET.get("open") == "1"

    if request.user.is_superuser or request.user.role in ["admin", "manager"]:
        if agent:
            news_items = news_items.filter(agent_id=agent)
    else:
        news_items = news_items.filter(agent=request.user)

    if search:
        news_items = news_items.filter(
            Q(related_property__street__icontains=search)
            | Q(related_property__number__icontains=search)
            | Q(related_property__city__icontains=search)
        )

    if motivation:
        news_items = news_items.filter(motivation=motivation)

    if status:
        news_items = news_items.filter(status=status)
    elif open_only:
        news_items = news_items.exclude(status="closed")

    ordering_options = {
        "recent": "-created_at",
        "oldest": "created_at",
        "address": "related_property__street",
    }
    news_items = paginate(
        request,
        news_items.order_by(ordering_options.get(ordering, "-created_at")),
    )

    return render(
        request,
        "news/list.html",
        {
            "news_items": news_items,
            "page_obj": news_items,
            "motivation_choices": News.MOTIVATION_CHOICES,
            "status_choices": News.STATUS_CHOICES,
            "agents": User.objects.filter(is_active=True).order_by("username"),
        },
    )


@login_required
def news_create(request, property_id=None):
    property_obj = None

    if property_id is not None:
        property_obj = get_object_or_404(Property, pk=property_id)

    form = NewsForm(
        request.POST or None,
        property_obj=property_obj,
        user=request.user,
    )

    if request.method == "POST" and form.is_valid():
        news = form.save(commit=False)

        if property_obj is not None:
            news.related_property = property_obj

        if "agent" not in form.fields:
            news.agent = request.user
        news.save()

        return redirect("news_detail", pk=news.pk)

    return render(
        request,
        "news/create.html",
        {
            "form": form,
            "property": property_obj,
            "page_title": "Nueva noticia",
            "submit_label": "Guardar noticia",
        },
    )


@login_required
def news_update(request, pk):
    news = get_object_or_404(scope_to_user(News.objects.all(), request.user), pk=pk)
    form = NewsForm(request.POST or None, instance=news, user=request.user)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("news_detail", pk=news.pk)

    return render(
        request,
        "news/create.html",
        {
            "form": form,
            "property": news.related_property,
            "page_title": "Editar noticia",
            "submit_label": "Guardar cambios",
            "news": news,
        },
    )


@login_required
def news_detail(request, pk):
    news = get_object_or_404(
        scope_to_user(
            News.objects.select_related("related_property", "agent"),
            request.user,
        ),
        pk=pk,
    )
    comments = news.comments.select_related("user").order_by("-created_at")
    timeline = []

    for comment in comments:
        timeline.append({
            "type": "comment",
            "date": comment.created_at,
            "object": comment,
        })

    for call in news.calls.all():
        timeline.append({
            "type": "call",
            "date": timezone.make_aware(datetime.combine(call.date, call.time)),
            "object": call,
        })

    for appointment in news.appointments.all():
        timeline.append({
            "type": "appointment",
            "date": timezone.make_aware(
                datetime.combine(appointment.date, appointment.time)
            ),
            "object": appointment,
        })

    timeline.sort(key=lambda item: item["date"], reverse=True)

    return render(
        request,
        "news/detail.html",
        {
            "news": news,
            "comments": comments,
            "form": NewsCommentForm(),
            "has_comments": bool(comments),
            "timeline": timeline,
        },
    )


@login_required
def news_delete(request, pk):
    news = get_object_or_404(
        scope_to_user(
            News.objects.select_related("related_property", "agent"),
            request.user,
        ),
        pk=pk,
    )

    will_close = (
        not can_manage_office(request.user)
        or has_related_records(news)
    )
    if request.method == "POST":
        if will_close:
            news.status = "closed"
            news.save(update_fields=["status"])
            messages.success(
                request,
                "La noticia se ha cerrado y su historial se conserva.",
            )
        else:
            news.delete()
            messages.success(request, "La noticia se ha eliminado definitivamente.")
        return redirect("news_list")

    return render(
        request,
        "news/delete.html",
        {"news": news, "will_archive": will_close},
    )


@login_required
@require_POST
def news_add_comment(request, pk):
    news = get_object_or_404(scope_to_user(News.objects.all(), request.user), pk=pk)
    form = NewsCommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.news = news
        comment.user = request.user
        comment.save()

    return redirect("news_detail", pk=news.pk)
