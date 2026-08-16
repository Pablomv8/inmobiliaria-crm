import json
from datetime import datetime, timedelta
from itertools import chain

from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
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


def build_worker_rows():
    workers = list(
        User.objects.filter(is_active=True, role="agent").order_by(
            "first_name",
            "last_name",
            "username",
        )
    )
    contact_counts = grouped_counts(Contact.objects.all(), "assigned_agent_id")
    news_counts = grouped_counts(News.objects.all(), "agent_id")
    open_news_counts = grouped_counts(
        News.objects.exclude(status="closed"),
        "agent_id",
    )
    listing_counts = grouped_counts(Listing.objects.all(), "agent_id")
    active_listing_counts = grouped_counts(
        Listing.objects.filter(status="active"),
        "agent_id",
    )
    order_counts = grouped_counts(Order.objects.all(), "buyer__assigned_agent_id")
    open_order_counts = grouped_counts(
        Order.objects.exclude(status__in=["closed", "cancelled"]),
        "buyer__assigned_agent_id",
    )
    scheduled_appointment_counts = grouped_counts(
        Appointment.objects.filter(status="scheduled"),
        "agent_id",
    )
    pending_call_counts = grouped_counts(
        Call.objects.filter(status="pending"),
        "agent_id",
    )
    pending_task_counts = grouped_counts(
        Task.objects.filter(status__in=["pending", "in_progress"]),
        "assigned_to_id",
    )
    proposal_counts = grouped_counts(ProposalAppointment.objects.all(), "agent_id")
    signed_sale_rows = {
        item["agent_id"]: item
        for item in Sale.objects.filter(status="signed")
        .values("agent_id")
        .annotate(total=Count("id"), revenue=Sum("sale_price"))
        if item["agent_id"] is not None
    }

    rows = []
    for worker in workers:
        scheduled_appointments = scheduled_appointment_counts.get(worker.pk, 0)
        pending_calls = pending_call_counts.get(worker.pk, 0)
        pending_tasks = pending_task_counts.get(worker.pk, 0)
        sale_data = signed_sale_rows.get(worker.pk, {})
        rows.append({
            "user": worker,
            "contacts": contact_counts.get(worker.pk, 0),
            "news": news_counts.get(worker.pk, 0),
            "open_news": open_news_counts.get(worker.pk, 0),
            "listings": listing_counts.get(worker.pk, 0),
            "active_listings": active_listing_counts.get(worker.pk, 0),
            "orders": order_counts.get(worker.pk, 0),
            "open_orders": open_order_counts.get(worker.pk, 0),
            "scheduled_appointments": scheduled_appointments,
            "pending_calls": pending_calls,
            "pending_tasks": pending_tasks,
            "pending_workload": scheduled_appointments + pending_calls + pending_tasks,
            "proposals": proposal_counts.get(worker.pk, 0),
            "signed_sales": sale_data.get("total", 0),
            "revenue": sale_data.get("revenue", 0) or 0,
        })
    return rows


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
    Property.refresh_aged_contact_statuses()
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
        .select_related("contact", "zone")
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
                status__in=[
                    "news",
                    "contacted",
                    "contacted_30",
                    "in_listing",
                ]
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


@login_required
def team_overview(request):
    if not user_can_see_office(request.user):
        raise PermissionDenied

    worker_rows = build_worker_rows()
    return render(
        request,
        "dashboard/team_overview.html",
        {
            "worker_rows": worker_rows,
            "worker_count": len(worker_rows),
            "total_contacts": sum(row["contacts"] for row in worker_rows),
            "total_active_listings": sum(
                row["active_listings"] for row in worker_rows
            ),
            "total_open_orders": sum(row["open_orders"] for row in worker_rows),
            "total_pending_workload": sum(
                row["pending_workload"] for row in worker_rows
            ),
        },
    )


@login_required
def team_member_detail(request, pk):
    if not user_can_see_office(request.user):
        raise PermissionDenied

    worker = get_object_or_404(User, pk=pk, role="agent", is_active=True)
    today = timezone.localdate()
    now = timezone.now()

    contacts = Contact.objects.filter(assigned_agent=worker)
    news = News.objects.filter(agent=worker)
    listings = Listing.objects.filter(agent=worker)
    orders = Order.objects.filter(buyer__assigned_agent=worker)
    appointments = Appointment.objects.filter(agent=worker)
    calls = Call.objects.filter(agent=worker)
    tasks = Task.objects.filter(assigned_to=worker)
    proposals = ProposalAppointment.objects.filter(agent=worker)
    sales = Sale.objects.filter(agent=worker)

    pending_tasks = tasks.filter(status__in=["pending", "in_progress"])
    overdue_tasks = pending_tasks.filter(due_date__lt=now)
    completed_tasks = tasks.filter(status="done").count()
    task_total = tasks.exclude(status="cancelled").count()
    completed_appointments = appointments.filter(status="completed").count()
    appointment_total = appointments.exclude(status="cancelled").count()
    closed_news = news.filter(status="closed").count()
    news_total = news.count()
    signed_sales = sales.filter(status="signed")

    commission_expression = ExpressionWrapper(
        F("sale_price") * F("commission_percent") / 100,
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    signed_sale_totals = signed_sales.aggregate(
        revenue=Sum("sale_price"),
        commission=Sum(commission_expression),
    )

    upcoming_appointments = list(
        appointments.filter(status="scheduled", date__gte=today)
        .select_related("contact", "related_property")
        .order_by("date", "time")[:8]
    )
    upcoming_calls = list(
        calls.filter(status="pending", date__gte=today)
        .select_related("contact")
        .order_by("date", "time")[:8]
    )
    for appointment in upcoming_appointments:
        appointment.team_event_type = "appointment"
    for call in upcoming_calls:
        call.team_event_type = "call"
    upcoming_events = sorted(
        chain(upcoming_appointments, upcoming_calls),
        key=lambda event: (event.date, event.time),
    )[:8]

    context = {
        "worker": worker,
        "today": today,
        "contacts_total": contacts.count(),
        "owners_total": contacts.filter(contact_type="owner").count(),
        "buyers_total": contacts.filter(contact_type="buyer").count(),
        "news_total": news_total,
        "open_news": news.exclude(status="closed").count(),
        "closed_news": closed_news,
        "news_completion_rate": round(closed_news * 100 / news_total) if news_total else 0,
        "listings_total": listings.count(),
        "active_listings": listings.filter(status="active").count(),
        "finished_listings": listings.filter(status__in=["sold", "rented"]).count(),
        "orders_total": orders.count(),
        "open_orders": orders.exclude(status__in=["closed", "cancelled"]).count(),
        "proposals_total": proposals.count(),
        "scheduled_appointments": appointments.filter(status="scheduled").count(),
        "completed_appointments": completed_appointments,
        "appointment_completion_rate": (
            round(completed_appointments * 100 / appointment_total)
            if appointment_total
            else 0
        ),
        "pending_calls": calls.filter(status="pending").count(),
        "completed_calls": calls.filter(status="completed").count(),
        "pending_tasks": pending_tasks.count(),
        "overdue_tasks": overdue_tasks.count(),
        "completed_tasks": completed_tasks,
        "task_completion_rate": (
            round(completed_tasks * 100 / task_total) if task_total else 0
        ),
        "signed_sales": signed_sales.count(),
        "sales_revenue": signed_sale_totals["revenue"] or 0,
        "sales_commission": signed_sale_totals["commission"] or 0,
        "upcoming_events": upcoming_events,
        "recent_contacts": contacts.order_by("-created_at")[:5],
        "recent_news": news.select_related("related_property").order_by("-created_at")[:5],
        "recent_listings": listings.select_related("property", "owner").order_by("-created_at")[:5],
        "recent_orders": orders.select_related("buyer", "zone").order_by("-created_at")[:5],
        "recent_activities": Activity.objects.filter(user=worker)
        .select_related("contact", "task")[:8],
    }
    return render(request, "dashboard/team_member_detail.html", context)
