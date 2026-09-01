from datetime import date, datetime, timedelta
from itertools import chain

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import TruncMonth
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from config.pagination import paginate

from activities.models import Activity
from calendar_app.models import Appointment, Call, ProposalAppointment
from contacts.models import Contact
from goals.models import Goal
from goals.services import build_goal_progress, calculate_progress
from listings.models import Listing
from news.models import News
from orders.models import Order
from properties.models import Property
from sales.models import RentalContract, Sale
from tasks.models import Task
from users.models import User
from users.permissions import can_manage_office

from .alerts import (
    ALERT_CATEGORIES,
    ALERT_PRIORITIES,
    build_alerts,
    summarize_alerts,
)
from .daily_work import build_daily_work


def home(request):
    return render(request, "dashboard/home.html")


@login_required
def alert_center(request):
    all_alerts = build_alerts(request.user)
    request._crm_alerts = all_alerts
    summary = summarize_alerts(all_alerts)

    priority = request.GET.get("priority", "")
    category = request.GET.get("category", "")
    agent = request.GET.get("agent", "")
    search = request.GET.get("search", "").strip().casefold()

    alerts = all_alerts
    if priority in ALERT_PRIORITIES:
        alerts = [item for item in alerts if item.priority == priority]
    if category in ALERT_CATEGORIES:
        alerts = [item for item in alerts if item.category == category]
    if can_manage_office(request.user) and agent.isdigit():
        alerts = [item for item in alerts if item.agent_id == int(agent)]
    if search:
        alerts = [
            item for item in alerts
            if search in f"{item.title} {item.description} {item.agent_name}".casefold()
        ]

    page = paginate(request, alerts, per_page=12)
    return render(request, "dashboard/alerts.html", {
        "alerts": page,
        "page_obj": page,
        "alert_summary": summary,
        "alert_categories": ALERT_CATEGORIES.items(),
        "alert_priorities": ALERT_PRIORITIES.items(),
        "can_filter_agents": can_manage_office(request.user),
        "alert_agents": User.objects.filter(
            is_active=True,
            role__in=["agent", "manager", "admin"],
        ).order_by("first_name", "last_name", "username"),
    })


@login_required
def daily_work(request):
    can_select_agent = can_manage_office(request.user)
    selected_user = request.user
    selected_id = request.GET.get("agent", "")
    selectable_users = User.objects.filter(
        is_active=True,
        role__in=["agent", "manager", "admin"],
    ).order_by("first_name", "last_name", "username")
    if can_select_agent and selected_id.isdigit():
        selected_user = get_object_or_404(selectable_users, pk=selected_id)

    viewer_alerts = build_alerts(request.user)
    request._crm_alerts = viewer_alerts
    if can_select_agent:
        personal_alerts = [
            item for item in viewer_alerts
            if item.agent_id == selected_user.pk
        ]
    else:
        personal_alerts = viewer_alerts
    work = build_daily_work(selected_user, personal_alerts)
    return render(request, "dashboard/daily_work.html", {
        **work,
        "selected_user": selected_user,
        "can_select_agent": can_select_agent,
        "selectable_users": selectable_users,
    })


def user_can_see_office(user):
    return user.is_superuser or user.role in ["admin", "manager"]


def grouped_counts(queryset, field):
    return {
        item[field]: item["total"]
        for item in queryset.values(field).annotate(total=Count("id"))
        if item[field] is not None
    }


def conversion_percentage(current, previous):
    if not previous:
        return 0
    return min(100, round(current * 100 / previous))


def get_funnel_period(request):
    date_from = parse_date(request.GET.get("funnel_from", ""))
    date_to = parse_date(request.GET.get("funnel_to", ""))
    if date_from and date_to and date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def filter_by_period(queryset, field, date_from=None, date_to=None):
    if date_from:
        queryset = queryset.filter(**{f"{field}__gte": date_from})
    if date_to:
        queryset = queryset.filter(**{f"{field}__lte": date_to})
    return queryset


def build_commercial_funnel(
    news,
    listings,
    appointments,
    proposals,
    sales,
    rentals,
    *,
    user=None,
    date_from=None,
    date_to=None,
):
    news = filter_by_period(news, "created_at__date", date_from, date_to)
    listings = filter_by_period(
        listings,
        "created_at__date",
        date_from,
        date_to,
    )
    appointments = filter_by_period(
        appointments,
        "date",
        date_from,
        date_to,
    )
    proposals = filter_by_period(
        proposals,
        "created_at__date",
        date_from,
        date_to,
    )
    sales = filter_by_period(sales, "sale_date", date_from, date_to)
    rentals = filter_by_period(
        rentals,
        "contract_date",
        date_from,
        date_to,
    )
    counts = [
        news.count(),
        listings.count(),
        appointments.filter(appointment_type="sale")
        .exclude(status="cancelled")
        .count(),
        proposals.count(),
        appointments.filter(appointment_type="contract")
        .exclude(status="cancelled")
        .count(),
        sales.filter(status="signed").count()
        + rentals.filter(status="signed").count(),
    ]
    labels = [
        "Noticias captadas",
        "Encargos formalizados",
        "Visitas de venta",
        "Propuestas de compra",
        "Citas de contrato",
        "Operaciones firmadas",
    ]
    agent_query = f"?agent={user.pk}" if user is not None else ""
    calendar_query = f"?agents={user.pk}" if user is not None else ""
    urls = [
        f"{reverse('news_list')}{agent_query}",
        f"{reverse('listing_list')}{agent_query}",
        f"{reverse('calendar')}{calendar_query}",
        f"{reverse('listing_list')}{agent_query}",
        f"{reverse('calendar')}{calendar_query}",
        f"{reverse('sale_list')}{agent_query}",
    ]
    stages = []
    largest_stage = max(counts, default=0)
    for index, (label, count) in enumerate(zip(labels, counts)):
        conversion = (
            conversion_percentage(count, counts[index - 1])
            if index
            else 100
        )
        stages.append({
            "label": label,
            "count": count,
            "url": urls[index],
            "conversion": conversion,
            "dropoff": 100 - conversion if index else 0,
            "width": (
                max(6, round(count * 100 / largest_stage))
                if count and largest_stage
                else 0
            ),
        })
    return {
        "stages": stages,
        "closing_rate": conversion_percentage(counts[-1], counts[0]),
        "period": {
            "date_from": date_from,
            "date_to": date_to,
            "from_value": date_from.isoformat() if date_from else "",
            "to_value": date_to.isoformat() if date_to else "",
            "active": bool(date_from or date_to),
        },
    }


@login_required
def commercial_funnel_data(request):
    scope = request.GET.get("scope", "personal")
    date_from, date_to = get_funnel_period(request)

    if scope == "office":
        if not user_can_see_office(request.user):
            raise PermissionDenied
        user = None
        news = News.objects.all()
        listings = Listing.objects.all()
        appointments = Appointment.objects.all()
        proposals = ProposalAppointment.objects.all()
        sales = Sale.objects.all()
        rentals = RentalContract.objects.all()
    elif scope == "agent":
        if not user_can_see_office(request.user):
            raise PermissionDenied
        user = get_object_or_404(
            User,
            pk=request.GET.get("agent_id"),
            role="agent",
            is_active=True,
        )
        news = News.objects.filter(agent=user)
        listings = Listing.objects.filter(agent=user)
        appointments = Appointment.objects.filter(agent=user)
        proposals = ProposalAppointment.objects.filter(agent=user)
        sales = Sale.objects.filter(agent=user)
        rentals = RentalContract.objects.filter(agent=user)
    elif scope == "personal":
        user = request.user
        news = News.objects.filter(agent=user)
        listings = Listing.objects.filter(agent=user)
        appointments = Appointment.objects.filter(agent=user)
        proposals = ProposalAppointment.objects.filter(agent=user)
        sales = Sale.objects.filter(agent=user)
        rentals = RentalContract.objects.filter(agent=user)
    else:
        return JsonResponse({"error": "Ámbito de embudo no válido."}, status=400)

    return JsonResponse(build_commercial_funnel(
        news,
        listings,
        appointments,
        proposals,
        sales,
        rentals,
        user=user,
        date_from=date_from,
        date_to=date_to,
    ))


def build_economic_summary(sales, rentals, *, user=None):
    signed_sales = sales.filter(status="signed")
    signed_rentals = rentals.filter(status="signed")
    sale_totals = signed_sales.aggregate(
        volume=Sum("sale_price"),
        commission=Sum("commission_amount"),
    )
    rental_totals = signed_rentals.aggregate(
        monthly_rent=Sum("rent_price"),
        owner_commission=Sum("owner_commission"),
        tenant_commission=Sum("tenant_commission"),
    )
    sale_commission = sale_totals["commission"] or 0
    rental_commission = (
        (rental_totals["owner_commission"] or 0)
        + (rental_totals["tenant_commission"] or 0)
    )
    agent_query = f"?agent={user.pk}" if user is not None else ""
    return {
        "closed_operations": signed_sales.count() + signed_rentals.count(),
        "signed_sales": signed_sales.count(),
        "signed_rentals": signed_rentals.count(),
        "sale_volume": sale_totals["volume"] or 0,
        "monthly_rent": rental_totals["monthly_rent"] or 0,
        "commission": sale_commission + rental_commission,
        "sales_url": f"{reverse('sale_list')}{agent_query}",
        "rentals_url": f"{reverse('rental_contract_list')}{agent_query}",
    }


def build_goal_rows(queryset, limit=4):
    goals = queryset.prefetch_related("assignees").order_by("end_date")[:limit]
    return [build_goal_progress(goal) for goal in goals]


def build_goal_summary(queryset):
    rows = [build_goal_progress(goal) for goal in queryset.prefetch_related(
        "assignees"
    )]
    active_count = len(rows)
    average_progress = (
        round(sum(row["percentage"] for row in rows) / active_count)
        if active_count
        else 0
    )
    achieved_count = sum(1 for row in rows if row["is_achieved"])
    today = timezone.localdate()
    at_risk_count = sum(
        1
        for row in rows
        if not row["is_achieved"]
        and row["goal"].end_date <= today + timedelta(days=7)
    )
    return {
        "active": active_count,
        "achieved": achieved_count,
        "at_risk": at_risk_count,
        "percentage": average_progress,
    }


def shift_month(month_start, offset):
    month_index = month_start.year * 12 + month_start.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def monthly_counts(queryset, field, start_date):
    rows = (
        queryset.filter(**{f"{field}__date__gte": start_date})
        .annotate(month=TruncMonth(field))
        .values("month")
        .annotate(total=Count("id"))
    )
    counts = {}
    for row in rows:
        month = row["month"]
        if isinstance(month, datetime):
            month = month.date()
        counts[month.replace(day=1)] = row["total"]
    return counts


def monthly_date_counts(queryset, field, start_date):
    rows = (
        queryset.filter(**{f"{field}__gte": start_date})
        .annotate(month=TruncMonth(field))
        .values("month")
        .annotate(total=Count("id"))
    )
    counts = {}
    for row in rows:
        month = row["month"]
        if isinstance(month, datetime):
            month = month.date()
        counts[month.replace(day=1)] = row["total"]
    return counts


def build_monthly_evolution(
    news,
    listings,
    orders,
    proposals,
    sales,
    rentals,
    months=6,
):
    current_month = timezone.localdate().replace(day=1)
    month_list = [
        shift_month(current_month, offset)
        for offset in range(-(months - 1), 1)
    ]
    start_date = month_list[0]
    news_map = monthly_counts(news, "created_at", start_date)
    listing_map = monthly_counts(listings, "created_at", start_date)
    order_map = monthly_counts(orders, "created_at", start_date)
    proposal_map = monthly_counts(proposals, "created_at", start_date)
    sale_map = monthly_date_counts(
        sales.filter(status="signed"),
        "sale_date",
        start_date,
    )
    rental_map = monthly_date_counts(
        rentals.filter(status="signed"),
        "contract_date",
        start_date,
    )
    return {
        "labels": [month.strftime("%m/%Y") for month in month_list],
        "news": [news_map.get(month, 0) for month in month_list],
        "listings": [listing_map.get(month, 0) for month in month_list],
        "orders": [order_map.get(month, 0) for month in month_list],
        "proposals": [proposal_map.get(month, 0) for month in month_list],
        "closings": [
            sale_map.get(month, 0) + rental_map.get(month, 0)
            for month in month_list
        ],
    }


def build_dashboard_analytics(
    *,
    goals,
    news,
    listings,
    orders,
    proposals,
    sales,
    rentals,
):
    return {
        "monthly": build_monthly_evolution(
            news,
            listings,
            orders,
            proposals,
            sales,
            rentals,
        ),
        "goals": build_goal_summary(goals),
    }


def build_agent_comparison(days):
    start_date = timezone.localdate() - timedelta(days=days - 1)
    users = list(
        User.objects.filter(
            is_active=True,
            role__in=["agent", "manager", "admin"],
        ).order_by("first_name", "last_name", "username")
    )
    contacts = grouped_counts(
        Contact.objects.filter(created_at__date__gte=start_date),
        "assigned_agent_id",
    )
    news = grouped_counts(
        News.objects.filter(created_at__date__gte=start_date),
        "agent_id",
    )
    listings = grouped_counts(
        Listing.objects.filter(created_at__date__gte=start_date),
        "agent_id",
    )
    orders = grouped_counts(
        Order.objects.filter(created_at__date__gte=start_date),
        "agent_id",
    )
    appointments = grouped_counts(
        Appointment.objects.filter(
            date__gte=start_date,
            status="completed",
        ),
        "agent_id",
    )
    rows = []
    for user in users:
        row = {
            "user": user,
            "contacts": contacts.get(user.pk, 0),
            "news": news.get(user.pk, 0),
            "listings": listings.get(user.pk, 0),
            "orders": orders.get(user.pk, 0),
            "appointments": appointments.get(user.pk, 0),
        }
        row["total"] = sum(
            row[key]
            for key in ("contacts", "news", "listings", "orders", "appointments")
        )
        rows.append(row)
    rows.sort(key=lambda row: (-row["total"], row["user"].username))
    rows = rows[:10]
    return {
        "labels": [
            row["user"].get_full_name() or row["user"].username
            for row in rows
        ],
        "contacts": [row["contacts"] for row in rows],
        "news": [row["news"] for row in rows],
        "listings": [row["listings"] for row in rows],
        "orders": [row["orders"] for row in rows],
        "appointments": [row["appointments"] for row in rows],
    }


def most_recent_value(item, fields):
    values = [getattr(item, field, None) for field in fields]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def build_opportunity_aging(news, listings, orders):
    now = timezone.now()
    activity_dates = []
    for item in news.exclude(status="closed").annotate(
        latest_comment=Max("comments__created_at"),
        latest_appointment=Max("appointments__created_at"),
        latest_call=Max("calls__created_at"),
    ):
        activity_dates.append(most_recent_value(item, [
            "created_at",
            "latest_comment",
            "latest_appointment",
            "latest_call",
        ]))
    for item in listings.filter(status="active").annotate(
        latest_comment=Max("comments__created_at"),
        latest_appointment=Max("follow_up_appointments__created_at"),
        latest_call=Max("calls__created_at"),
        latest_proposal=Max("proposals__created_at"),
    ):
        activity_dates.append(most_recent_value(item, [
            "created_at",
            "latest_comment",
            "latest_appointment",
            "latest_call",
            "latest_proposal",
        ]))
    for item in orders.exclude(status__in=["closed", "cancelled"]).annotate(
        latest_comment=Max("comments__created_at"),
        latest_appointment=Max("sale_appointments__created_at"),
        latest_proposal=Max("proposals__created_at"),
    ):
        activity_dates.append(most_recent_value(item, [
            "created_at",
            "updated_at",
            "latest_comment",
            "latest_appointment",
            "latest_proposal",
        ]))

    buckets = [0, 0, 0, 0]
    for last_activity in activity_dates:
        if last_activity is None:
            continue
        age = max(0, (now - last_activity).days)
        if age <= 7:
            buckets[0] += 1
        elif age <= 15:
            buckets[1] += 1
        elif age <= 30:
            buckets[2] += 1
        else:
            buckets[3] += 1
    total = sum(buckets)
    return {
        "labels": ["0–7 días", "8–15 días", "16–30 días", "+30 días"],
        "counts": buckets,
        "total": total,
        "stale": buckets[3],
        "fresh_percentage": round(buckets[0] * 100 / total) if total else 0,
    }


def build_appointment_outcomes(appointments, days=90):
    start_date = timezone.localdate() - timedelta(days=days - 1)
    appointments = appointments.filter(date__gte=start_date)
    groups = [
        ("Adquisición", ["acquisition"]),
        ("Venta", ["sale"]),
        ("Seguimiento", ["follow_up"]),
        ("Propuesta", ["proposal"]),
        ("Aceptación", ["proposal_acceptance"]),
        ("Contrato/firma", ["contract", "signing"]),
        ("Asesoramiento financiero", ["financial_advice"]),
    ]
    data = {
        "labels": [],
        "successful": [],
        "unsuccessful": [],
        "without_result": [],
        "cancelled": [],
        "period_days": days,
    }
    for label, appointment_types in groups:
        group = appointments.filter(appointment_type__in=appointment_types)
        successful = group.filter(status="completed", result_success=True).count()
        unsuccessful = group.filter(status="completed", result_success=False).count()
        without_result = group.filter(
            status="completed",
            result_success__isnull=True,
        ).count()
        cancelled = group.filter(status="cancelled").count()
        if successful + unsuccessful + without_result + cancelled == 0:
            continue
        data["labels"].append(label)
        data["successful"].append(successful)
        data["unsuccessful"].append(unsuccessful)
        data["without_result"].append(without_result)
        data["cancelled"].append(cancelled)
    data["total"] = sum(
        sum(data[key])
        for key in ("successful", "unsuccessful", "without_result", "cancelled")
    )
    decided = sum(data["successful"]) + sum(data["unsuccessful"])
    data["success_rate"] = (
        round(sum(data["successful"]) * 100 / decided) if decided else 0
    )
    return data


def build_listing_health(listings):
    today = timezone.localdate()
    follow_up_cutoff = today - timedelta(days=30)
    active_listings = list(listings.filter(status="active"))
    listing_ids = [listing.pk for listing in active_listings]
    follow_up_dates = {
        row["listing_id"]: row["latest"]
        for row in Appointment.objects.filter(
            listing_id__in=listing_ids,
            appointment_type="follow_up",
        ).exclude(status="cancelled").values("listing_id").annotate(
            latest=Max("date")
        )
    }
    proposal_listing_ids = set(
        ProposalAppointment.objects.filter(
            listing_id__in=listing_ids,
        ).values_list("listing_id", flat=True)
    )
    expiring_ids = {
        listing.pk
        for listing in active_listings
        if listing.end_date
        and today <= listing.end_date <= today + timedelta(days=30)
    }
    without_recent_follow_up_ids = {
        listing.pk
        for listing in active_listings
        if follow_up_dates.get(listing.pk) is None
        or follow_up_dates[listing.pk] < follow_up_cutoff
    }
    needs_attention_ids = expiring_ids | without_recent_follow_up_ids
    healthy = len(active_listings) - len(needs_attention_ids)
    total = len(active_listings)
    return {
        "total": total,
        "healthy": healthy,
        "healthy_percentage": round(healthy * 100 / total) if total else 0,
        "needs_attention": len(needs_attention_ids),
        "expiring": len(expiring_ids),
        "without_recent_follow_up": len(without_recent_follow_up_ids),
        "with_proposals": len(proposal_listing_ids),
    }


def build_commercial_health(*, news, listings, orders, appointments):
    return {
        "aging": build_opportunity_aging(news, listings, orders),
        "appointments": build_appointment_outcomes(appointments),
        "listings": build_listing_health(listings),
    }


def build_action_items(
    *,
    user,
    appointments,
    listings,
    orders,
    tasks,
    properties,
    office=False,
):
    today = timezone.localdate()
    now = timezone.now()
    agent_query = "" if office else f"?agent={user.pk}"
    calendar_query = "" if office else f"?agents={user.pk}"
    orders_without_visit = orders.exclude(
        status__in=["closed", "cancelled"]
    ).annotate(
        sale_visit_count=Count(
            "sale_appointments",
            filter=(
                Q(sale_appointments__appointment_type="sale")
                & ~Q(sale_appointments__status="cancelled")
            ),
        )
    ).filter(sale_visit_count=0).count()
    return [
        {
            "label": "Tareas vencidas",
            "count": tasks.filter(
                status__in=["pending", "in_progress"],
                due_date__lt=now,
            ).count(),
            "url": f"{reverse('task_list')}{agent_query}",
            "tone": "red",
        },
        {
            "label": "Adquisiciones por decidir",
            "count": appointments.filter(
                appointment_type="acquisition",
                status="completed",
                result_success__isnull=True,
            ).count(),
            "url": f"{reverse('calendar')}{calendar_query}",
            "tone": "amber",
        },
        {
            "label": "Visitas de venta por decidir",
            "count": appointments.filter(
                appointment_type="sale",
                status="completed",
                result_success__isnull=True,
            ).count(),
            "url": f"{reverse('calendar')}{calendar_query}",
            "tone": "amber",
        },
        {
            "label": "Ofertas por registrar",
            "count": appointments.filter(
                appointment_type="proposal",
                status="completed",
                proposal__isnull=True,
            ).count(),
            "url": f"{reverse('calendar')}{calendar_query}",
            "tone": "violet",
        },
        {
            "label": "Pedidos sin cita de venta",
            "count": orders_without_visit,
            "url": f"{reverse('order_list')}{agent_query}",
            "tone": "blue",
        },
        {
            "label": "Encargos que vencen en 30 días",
            "count": listings.filter(
                status="active",
                end_date__gte=today,
                end_date__lte=today + timedelta(days=30),
            ).count(),
            "url": f"{reverse('listing_list')}{agent_query}",
            "tone": "orange",
        },
        {
            "label": "Inmuebles sin contacto reciente",
            "count": properties.filter(
                status__in=["never_contacted", "contacted_30"],
            ).count(),
            "url": reverse("properties"),
            "tone": "gray",
        },
    ]


def build_user_rows():
    users = list(User.objects.filter(is_active=True).order_by("role", "username"))
    listing_counts = grouped_counts(Listing.objects.all(), "agent_id")
    active_listing_counts = grouped_counts(
        Listing.objects.filter(status="active"),
        "agent_id",
    )
    order_counts = grouped_counts(Order.objects.all(), "agent_id")
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
    order_counts = grouped_counts(Order.objects.all(), "agent_id")
    open_order_counts = grouped_counts(
        Order.objects.exclude(status__in=["closed", "cancelled"]),
        "agent_id",
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


@login_required
def dashboard(request):
    Property.refresh_aged_contact_statuses()
    user = request.user
    today = timezone.localdate()
    now = timezone.now()
    is_office_viewer = user_can_see_office(user)
    dashboard_view = request.GET.get("view", "personal")
    if not is_office_viewer or dashboard_view not in {
        "personal",
        "office",
        "both",
    }:
        dashboard_view = "personal"
    show_personal_dashboard = dashboard_view in {"personal", "both"}
    show_office_dashboard = (
        is_office_viewer and dashboard_view in {"office", "both"}
    )
    funnel_date_from, funnel_date_to = get_funnel_period(request)

    personal_contacts = Contact.objects.filter(assigned_agent=user)
    personal_tasks = Task.objects.filter(assigned_to=user)
    personal_listings = Listing.objects.filter(agent=user)
    personal_orders = Order.objects.filter(agent=user)
    personal_news = News.objects.filter(agent=user)
    personal_appointments = Appointment.objects.filter(agent=user)
    personal_calls = Call.objects.filter(agent=user)
    personal_proposals = ProposalAppointment.objects.filter(agent=user)
    personal_sales = Sale.objects.filter(agent=user)
    personal_rentals = RentalContract.objects.filter(agent=user)
    personal_properties = Property.objects.filter(
        Q(created_by=user)
        | Q(listings__agent=user)
        | Q(contacts__assigned_agent=user)
    ).distinct()

    personal_funnel = build_commercial_funnel(
        personal_news,
        personal_listings,
        personal_appointments,
        personal_proposals,
        personal_sales,
        personal_rentals,
        user=user,
        date_from=funnel_date_from,
        date_to=funnel_date_to,
    )
    personal_economics = build_economic_summary(
        personal_sales,
        personal_rentals,
        user=user,
    )
    personal_goals = Goal.objects.filter(
        assignees=user,
        start_date__lte=today,
        end_date__gte=today,
    ).distinct()
    personal_goal_rows = build_goal_rows(personal_goals)
    personal_analytics = build_dashboard_analytics(
        goals=personal_goals,
        news=personal_news,
        listings=personal_listings,
        orders=personal_orders,
        proposals=personal_proposals,
        sales=personal_sales,
        rentals=personal_rentals,
    )
    personal_commercial_health = build_commercial_health(
        news=personal_news,
        listings=personal_listings,
        orders=personal_orders,
        appointments=personal_appointments,
    )
    personal_action_items = build_action_items(
        user=user,
        appointments=personal_appointments,
        listings=personal_listings,
        orders=personal_orders,
        tasks=personal_tasks,
        properties=personal_properties,
    )

    signed_sales = personal_sales.filter(status="signed")
    personal_revenue = signed_sales.aggregate(total=Sum("sale_price"))["total"] or 0
    personal_commission = (
        signed_sales.aggregate(total=Sum("commission_amount"))["total"] or 0
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

    chart_is_office = show_office_dashboard

    context = {
        "is_office_viewer": is_office_viewer,
        "dashboard_view": dashboard_view,
        "show_personal_dashboard": show_personal_dashboard,
        "show_office_dashboard": show_office_dashboard,
        "chart_is_office": chart_is_office,
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
        "my_signed_rentals": personal_rentals.filter(status="signed").count(),
        "my_revenue": personal_revenue,
        "my_commission": personal_commission,
        "personal_funnel": personal_funnel,
        "personal_economics": personal_economics,
        "personal_goal_rows": personal_goal_rows,
        "personal_analytics": personal_analytics,
        "personal_commercial_health": personal_commercial_health,
        "personal_action_items": personal_action_items,
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
            if chart_is_office
            else Activity.objects.filter(user=user)
        ).select_related("user")[:6],
    }

    if show_office_dashboard:
        all_signed_sales = Sale.objects.filter(status="signed")
        agent_comparisons = {
            str(days): build_agent_comparison(days)
            for days in (7, 30, 90)
        }
        office_funnel = build_commercial_funnel(
            News.objects.all(),
            Listing.objects.all(),
            Appointment.objects.all(),
            ProposalAppointment.objects.all(),
            Sale.objects.all(),
            RentalContract.objects.all(),
            date_from=funnel_date_from,
            date_to=funnel_date_to,
        )
        office_economics = build_economic_summary(
            Sale.objects.all(),
            RentalContract.objects.all(),
        )
        office_goals = Goal.objects.filter(
            start_date__lte=today,
            end_date__gte=today,
        ).distinct()
        office_goal_rows = build_goal_rows(office_goals, limit=3)
        office_analytics = build_dashboard_analytics(
            goals=office_goals,
            news=News.objects.all(),
            listings=Listing.objects.all(),
            orders=Order.objects.all(),
            proposals=ProposalAppointment.objects.all(),
            sales=Sale.objects.all(),
            rentals=RentalContract.objects.all(),
        )
        office_commercial_health = build_commercial_health(
            news=News.objects.all(),
            listings=Listing.objects.all(),
            orders=Order.objects.all(),
            appointments=Appointment.objects.all(),
        )
        office_action_items = build_action_items(
            user=user,
            appointments=Appointment.objects.all(),
            listings=Listing.objects.all(),
            orders=Order.objects.all(),
            tasks=Task.objects.all(),
            properties=Property.objects.all(),
            office=True,
        )
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
            "office_funnel": office_funnel,
            "office_economics": office_economics,
            "office_goal_rows": office_goal_rows,
            "office_analytics": office_analytics,
            "office_commercial_health": office_commercial_health,
            "agent_comparison": agent_comparisons[str(selected_days)],
            "agent_comparisons": agent_comparisons,
            "office_action_items": office_action_items,
            "user_rows": build_user_rows(),
        })

    return render(request, "dashboard/home.html", context)


@login_required
def administration(request):
    if not user_can_see_office(request.user):
        raise PermissionDenied

    Property.refresh_aged_contact_statuses()
    today = timezone.localdate()
    all_properties = Property.objects.all()
    all_appointments = Appointment.objects.all()
    all_listings = Listing.objects.all()
    all_orders = Order.objects.all()
    all_sales = Sale.objects.all()
    all_rentals = RentalContract.objects.all()
    funnel_date_from, funnel_date_to = get_funnel_period(request)

    property_status_rows = [
        {
            "value": value,
            "label": label,
            "count": all_properties.filter(status=value).count(),
        }
        for value, label in Property.STATUS_CHOICES
    ]
    occupancy_rows = [
        {
            "value": value,
            "label": label,
            "count": all_properties.filter(occupied_by=value).count(),
        }
        for value, label in Property.OCCUPANCY_CHOICES
    ]
    proposal_status_rows = [
        {
            "value": value,
            "label": label,
            "count": ProposalAppointment.objects.filter(status=value).count(),
        }
        for value, label in ProposalAppointment.STATUS_CHOICES
    ]

    return render(
        request,
        "dashboard/administration.html",
        {
            "today": today,
            "office_users": User.objects.filter(is_active=True).count(),
            "office_contacts": Contact.objects.count(),
            "office_properties": all_properties.count(),
            "office_active_listings": all_listings.filter(status="active").count(),
            "office_open_orders": all_orders.exclude(
                status__in=["closed", "cancelled"]
            ).count(),
            "office_scheduled_appointments": all_appointments.filter(
                status="scheduled"
            ).count(),
            "office_proposals": ProposalAppointment.objects.count(),
            "office_closed_operations": (
                all_sales.filter(status="signed").count()
                + all_rentals.filter(status="signed").count()
            ),
            "office_action_items": build_action_items(
                user=request.user,
                appointments=all_appointments,
                listings=all_listings,
                orders=all_orders,
                tasks=Task.objects.all(),
                properties=all_properties,
                office=True,
            ),
            "office_funnel": build_commercial_funnel(
                News.objects.all(),
                all_listings,
                all_appointments,
                ProposalAppointment.objects.all(),
                all_sales,
                all_rentals,
                date_from=funnel_date_from,
                date_to=funnel_date_to,
            ),
            "office_economics": build_economic_summary(
                all_sales,
                all_rentals,
            ),
            "office_goal_rows": build_goal_rows(
                Goal.objects.filter(
                    start_date__lte=today,
                    end_date__gte=today,
                ).distinct(),
                limit=3,
            ),
            "property_status_rows": property_status_rows,
            "occupancy_rows": occupancy_rows,
            "proposal_status_rows": proposal_status_rows,
            "user_rows": build_user_rows(),
        },
    )


@login_required
def team_overview(request):
    if not user_can_see_office(request.user):
        raise PermissionDenied

    worker_rows = build_worker_rows()
    worker_count = len(worker_rows)
    total_contacts = sum(row["contacts"] for row in worker_rows)
    total_active_listings = sum(
        row["active_listings"] for row in worker_rows
    )
    total_open_orders = sum(row["open_orders"] for row in worker_rows)
    total_pending_workload = sum(
        row["pending_workload"] for row in worker_rows
    )
    worker_rows = paginate(request, worker_rows, per_page=10)
    return render(
        request,
        "dashboard/team_overview.html",
        {
            "worker_rows": worker_rows,
            "page_obj": worker_rows,
            "worker_count": worker_count,
            "total_contacts": total_contacts,
            "total_active_listings": total_active_listings,
            "total_open_orders": total_open_orders,
            "total_pending_workload": total_pending_workload,
        },
    )


@login_required
def team_member_detail(request, pk):
    if not user_can_see_office(request.user):
        raise PermissionDenied

    worker = get_object_or_404(User, pk=pk, role="agent", is_active=True)
    today = timezone.localdate()
    now = timezone.now()
    funnel_date_from, funnel_date_to = get_funnel_period(request)

    contacts = Contact.objects.filter(assigned_agent=worker)
    news = News.objects.filter(agent=worker)
    listings = Listing.objects.filter(agent=worker)
    orders = Order.objects.filter(agent=worker)
    appointments = Appointment.objects.filter(agent=worker)
    calls = Call.objects.filter(agent=worker)
    tasks = Task.objects.filter(assigned_to=worker)
    proposals = ProposalAppointment.objects.filter(agent=worker)
    sales = Sale.objects.filter(agent=worker)
    rentals = RentalContract.objects.filter(agent=worker)

    worker_funnel = build_commercial_funnel(
        news,
        listings,
        appointments,
        proposals,
        sales,
        rentals,
        user=worker,
        date_from=funnel_date_from,
        date_to=funnel_date_to,
    )

    pending_tasks = tasks.filter(status__in=["pending", "in_progress"])
    overdue_tasks = pending_tasks.filter(due_date__lt=now)
    completed_tasks = tasks.filter(status="done").count()
    task_total = tasks.exclude(status="cancelled").count()
    completed_appointments = appointments.filter(status="completed").count()
    appointment_total = appointments.exclude(status="cancelled").count()
    closed_news = news.filter(status="closed").count()
    news_total = news.count()
    signed_sales = sales.filter(status="signed")
    started_goal_progress = [
        build_goal_progress(goal)
        for goal in Goal.objects.filter(
            assignees=worker,
            start_date__lte=today,
        ).prefetch_related("assignees").distinct()
    ]
    started_goals = len(started_goal_progress)
    achieved_goals = sum(
        1 for row in started_goal_progress if row["is_achieved"]
    )
    goal_completion_rate = (
        round(achieved_goals * 100 / started_goals)
        if started_goals
        else 0
    )
    worker_goal_rows = build_goal_rows(
        Goal.objects.filter(
            assignees=worker,
            start_date__lte=today,
            end_date__gte=today,
        ).distinct(),
        limit=6,
    )
    for row in worker_goal_rows:
        row["show_contribution"] = True
        row["contribution_current"] = calculate_progress(
            row["goal"],
            [worker.pk],
        )

    signed_sale_totals = signed_sales.aggregate(
        revenue=Sum("sale_price"),
        commission=Sum("commission_amount"),
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
        "owners_total": contacts.filter(is_owner=True).count(),
        "buyers_total": contacts.filter(is_buyer=True).count(),
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
        "started_goals": started_goals,
        "achieved_goals": achieved_goals,
        "goal_completion_rate": goal_completion_rate,
        "worker_goal_rows": worker_goal_rows,
        "worker_funnel": worker_funnel,
        "upcoming_events": upcoming_events,
        "recent_contacts": contacts.order_by("-created_at")[:5],
        "recent_news": news.select_related("related_property").order_by("-created_at")[:5],
        "recent_listings": listings.select_related("property", "owner").order_by("-created_at")[:5],
        "recent_orders": orders.select_related("buyer", "zone").order_by("-created_at")[:5],
        "recent_activities": Activity.objects.filter(user=worker)
        .select_related("contact", "task")[:8],
    }
    return render(request, "dashboard/team_member_detail.html", context)
