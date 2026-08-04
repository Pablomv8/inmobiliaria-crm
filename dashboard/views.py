import json
from datetime import datetime, timedelta
from itertools import chain

from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from activities.models import Activity
from calendar_app.models import Appointment, Call, ProposalAppointment
from contacts.models import Contact
from listings.models import Listing
from news.models import News
from orders.models import Order
from properties.models import Property
from sales.models import Sale
from tasks.models import Task
from users.models import User


def home(request):
    return render(request, "dashboard/home.html")


def user_can_see_office(user):
    return user.is_superuser or user.role in ["admin", "manager"]


def grouped_counts(queryset, field):
    return {
        item[field]: item["total"]
        for item in queryset.values(field).annotate(total=Count("id"))
        if item[field] is not None
    }


def build_user_rows():
    users = list(User.objects.filter(is_active=True).order_by("role", "username"))
    listing_counts = grouped_counts(Listing.objects.all(), "agent_id")
    active_listing_counts = grouped_counts(
        Listing.objects.filter(status="active"),
        "agent_id",
    )
    order_counts = grouped_counts(Order.objects.all(), "buyer__assigned_agent_id")
    contact_counts = grouped_counts(Contact.objects.all(), "assigned_agent_id")
    news_counts = grouped_counts(
        News.objects.exclude(status="closed"),
        "agent_id",
    )
    appointment_counts = grouped_counts(
        Appointment.objects.filter(status="scheduled"),
        "agent_id",
    )
    task_counts = grouped_counts(
        Task.objects.filter(status__in=["pending", "in_progress"]),
        "assigned_to_id",
    )
    proposal_counts = grouped_counts(ProposalAppointment.objects.all(), "agent_id")

    return [
        {
            "user": member,
            "contacts": contact_counts.get(member.pk, 0),
            "listings": listing_counts.get(member.pk, 0),
            "active_listings": active_listing_counts.get(member.pk, 0),
            "orders": order_counts.get(member.pk, 0),
            "news": news_counts.get(member.pk, 0),
            "appointments": appointment_counts.get(member.pk, 0),
            "tasks": task_counts.get(member.pk, 0),
            "proposals": proposal_counts.get(member.pk, 0),
        }
        for member in users
    ]


def build_activity_chart(days, news, appointments, proposals):
    today = timezone.localdate()
    start_date = today - timedelta(days=days - 1)
    news_map = {
        item["day"]: item["total"]
        for item in news.filter(created_at__date__gte=start_date)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
    }
    appointments_map = {
        item["date"]: item["total"]
        for item in appointments.filter(
            status="completed",
            date__gte=start_date,
        )
        .values("date")
        .annotate(total=Count("id"))
    }
    proposals_map = {
        item["day"]: item["total"]
        for item in proposals.filter(created_at__date__gte=start_date)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
    }

    dates = [start_date + timedelta(days=offset) for offset in range(days)]
    return {
        "activity_labels": json.dumps([day.strftime("%d/%m") for day in dates]),
        "news_data": json.dumps([news_map.get(day, 0) for day in dates]),
        "appointments_data": json.dumps(
            [appointments_map.get(day, 0) for day in dates]
        ),
        "proposals_data": json.dumps(
            [proposals_map.get(day, 0) for day in dates]
        ),
    }


@login_required
def dashboard(request):
    user = request.user
    today = timezone.localdate()
    now = timezone.now()
    is_office_viewer = user_can_see_office(user)

    personal_contacts = Contact.objects.filter(assigned_agent=user)
    personal_tasks = Task.objects.filter(assigned_to=user)
    personal_listings = Listing.objects.filter(agent=user)
    personal_orders = Order.objects.filter(buyer__assigned_agent=user)
    personal_news = News.objects.filter(agent=user)
    personal_appointments = Appointment.objects.filter(agent=user)
    personal_calls = Call.objects.filter(agent=user)
    personal_proposals = ProposalAppointment.objects.filter(agent=user)
    personal_sales = Sale.objects.filter(agent=user)
    personal_properties = Property.objects.filter(
        listings__agent=user,
    ).distinct()

    signed_sales = personal_sales.filter(status="signed")
    personal_revenue = signed_sales.aggregate(total=Sum("sale_price"))["total"] or 0
    commission_expression = ExpressionWrapper(
        F("sale_price") * F("commission_percent") / 100,
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    personal_commission = (
        signed_sales.aggregate(total=Sum(commission_expression))["total"] or 0
    )

    upcoming_appointments = list(
        personal_appointments.filter(
            status="scheduled",
            date__gte=today,
        ).select_related("contact", "related_property")
    )
    upcoming_calls = list(
        personal_calls.filter(
            status="pending",
            date__gte=today,
        ).select_related("contact")
    )
    for appointment in upcoming_appointments:
        appointment.dashboard_type = "appointment"
    for call in upcoming_calls:
        call.dashboard_type = "call"
    upcoming_events = sorted(
        chain(upcoming_appointments, upcoming_calls),
        key=lambda event: (event.date, event.time),
    )[:8]

    pending_tasks = personal_tasks.filter(status__in=["pending", "in_progress"])
    overdue_tasks = pending_tasks.filter(due_date__lt=now)
    upcoming_tasks = (
        pending_tasks.filter(due_date__gte=now)
        .select_related("contact")
        .order_by("due_date")[:6]
    )
    acquisition_decisions = personal_appointments.filter(
        appointment_type="acquisition",
        status="completed",
        result_success__isnull=True,
    ).count()
    sale_decisions = personal_appointments.filter(
        appointment_type="sale",
        status="completed",
        result_success__isnull=True,
    ).count()
    offers_to_register = personal_appointments.filter(
        appointment_type="proposal",
        status="completed",
        proposal__isnull=True,
    ).count()
    expiring_listings = personal_listings.filter(
        status="active",
        end_date__gte=today,
        end_date__lte=today + timedelta(days=30),
    ).count()

    try:
        selected_days = int(request.GET.get("days", 30))
    except (TypeError, ValueError):
        selected_days = 30
    if selected_days not in [7, 30, 90]:
        selected_days = 30

    chart_news = News.objects.all() if is_office_viewer else personal_news
    chart_appointments = (
        Appointment.objects.all() if is_office_viewer else personal_appointments
    )
    chart_proposals = (
        ProposalAppointment.objects.all()
        if is_office_viewer
        else personal_proposals
    )
    chart_context = build_activity_chart(
        selected_days,
        chart_news,
        chart_appointments,
        chart_proposals,
    )

    context = {
        "is_office_viewer": is_office_viewer,
        "today": today,
        "selected_days": selected_days,
        "my_contacts": personal_contacts.count(),
        "my_properties": personal_properties.count(),
        "my_listings": personal_listings.count(),
        "my_active_listings": personal_listings.filter(status="active").count(),
        "my_orders": personal_orders.count(),
        "my_open_news": personal_news.exclude(status="closed").count(),
        "my_scheduled_appointments": personal_appointments.filter(
            status="scheduled"
        ).count(),
        "my_pending_calls": personal_calls.filter(status="pending").count(),
        "my_pending_tasks": pending_tasks.count(),
        "my_overdue_tasks": overdue_tasks.count(),
        "my_proposals": personal_proposals.count(),
        "my_signed_sales": signed_sales.count(),
        "my_revenue": personal_revenue,
        "my_commission": personal_commission,
        "upcoming_events": upcoming_events,
        "upcoming_tasks": upcoming_tasks,
        "acquisition_decisions": acquisition_decisions,
        "sale_decisions": sale_decisions,
        "offers_to_register": offers_to_register,
        "expiring_listings": expiring_listings,
        "recent_listings": personal_listings.select_related(
            "property",
            "owner",
        ).order_by("-created_at")[:5],
        "recent_orders": personal_orders.select_related(
            "buyer",
            "zone",
        ).order_by("-created_at")[:5],
        "recent_activities": (
            Activity.objects.all()
            if is_office_viewer
            else Activity.objects.filter(user=user)
        ).select_related("user")[:6],
        **chart_context,
    }

    if is_office_viewer:
        all_signed_sales = Sale.objects.filter(status="signed")
        context.update({
            "office_users": User.objects.filter(is_active=True).count(),
            "office_contacts": Contact.objects.count(),
            "office_properties": Property.objects.count(),
            "office_active_properties": Property.objects.filter(
                status="active"
            ).count(),
            "office_listings": Listing.objects.count(),
            "office_active_listings": Listing.objects.filter(
                status="active"
            ).count(),
            "office_orders": Order.objects.count(),
            "office_open_news": News.objects.exclude(status="closed").count(),
            "office_scheduled_appointments": Appointment.objects.filter(
                status="scheduled"
            ).count(),
            "office_pending_calls": Call.objects.filter(status="pending").count(),
            "office_proposals": ProposalAppointment.objects.count(),
            "office_signed_sales": all_signed_sales.count(),
            "office_revenue": (
                all_signed_sales.aggregate(total=Sum("sale_price"))["total"] or 0
            ),
            "user_rows": build_user_rows(),
        })

    return render(request, "dashboard/home.html", context)
