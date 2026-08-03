from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, F, DecimalField, ExpressionWrapper
from django.utils import timezone
from datetime import timedelta
from sales.models import Sale
import json

from django.db.models import Count
from django.db.models.functions import TruncDate

from contacts.models import Contact
from properties.models import Property
from tasks.models import Task
from activities.models import Activity
from collections import defaultdict

today = timezone.now().date()
start = today - timedelta(days=30)
previous_start = today - timedelta(days=60)
previous_end = today - timedelta(days=30)



def growth(current, previous):

    if previous == 0:
        if current > 0:
            return 100, "up"
        return 0, "flat"

    change = ((current - previous) / previous) * 100
    change = round(change, 1)

    if change > 0:
        return change, "up"
    elif change < 0:
        return change, "down"
    return change, "flat"

def home(request):
    return render(request, 'dashboard/home.html')

@login_required
def dashboard(request):

    user = request.user

    labels = []
    contacts_data = []
    sales_data = []
    tasks_data = []
    selected_days=[]
    contacts_current = Contact.objects.filter(
        created_at__date__gte=start
    ).count()

    contacts_previous = Contact.objects.filter(
        created_at__date__gte=previous_start,
        created_at__date__lt=start
    ).count()

    sales_current = Sale.objects.filter(
        sale_date__gte=start, status= 'signed'
    ).count()

    sales_previous = Sale.objects.filter(
        sale_date__gte=previous_start,
        sale_date__lt=start, status='signed'
    ).count()

    revenue_current = Sale.objects.filter(
        sale_date__gte=start, status = 'signed'
    ).aggregate(total=Sum("sale_price"))["total"] or 0

    revenue_previous = Sale.objects.filter(
        sale_date__gte=previous_start,
        sale_date__lt=start, status = 'signed'
    ).aggregate(total=Sum("sale_price"))["total"] or 0


    if user.role in ["admin", "manager"]:

        contacts = Contact.objects.all()
        tasks = Task.objects.all()

        total_properties = Property.objects.count()

        recent_activities = Activity.objects.all()[:6]

        sales = Sale.objects.select_related(
            "agent",
            "buyer",
            "related_property"
        )

    else:

        contacts = Contact.objects.filter(
            assigned_agent=user
        )

        tasks = Task.objects.filter(
            assigned_to=user
        )
        recent_activities = Activity.objects.filter(
            user=request.user
        )[:6]

        total_properties = None

        sales = Sale.objects.filter(
            agent=user
        ).select_related(
            "buyer",
            "related_property"
        )

    total_contacts = contacts.count()

    total_tasks = tasks.count()

    pending_tasks = tasks.filter(
        status="pending"
    ).count()

    overdue_tasks = tasks.filter(
        status__in=["pending", "in_progress"],
        due_date__lt=timezone.now()
    ).count()


    latest_contacts = contacts.order_by(
        "-created_at"
    )[:5]

    latest_tasks = tasks.order_by(
        "-created_at"
    )[:5]
    

    upcoming_tasks = tasks.filter(
        due_date__isnull=False,
        due_date__gte=timezone.now()
    ).exclude(status= "done").order_by("due_date")[:5]

    completed_tasks = tasks.filter(
        status="done"
    ).order_by("-updated_at")[:5]

    sales_completed = sales.filter(
        status="completed"
    )

    total_revenue = (
        sales_completed.aggregate(
            total=Sum("sale_price")
        )["total"]
        or 0
    )

    completed_sales_count = sales_completed.count()

    average_sale = (
        sales_completed.aggregate(
            avg=Avg("sale_price")
        )["avg"]
        or 0
    )

    commission_expression = ExpressionWrapper(
        F("sale_price") * F("commission_percent") / 100,
        output_field=DecimalField(
            max_digits=12,
            decimal_places=2
        )
    )

    total_commission = (
        sales_completed.aggregate(
            total=Sum(commission_expression)
        )["total"]
        or 0
    )

    recent_sales = sales_completed.order_by(
        "-sale_date"
    )[:5]

    top_agents = []

    if user.role in ["admin", "manager"]:

        top_agents = (
            Sale.objects.filter(
                status="completed"
            )
            .values(
                "agent__username"
            )
            .annotate(
                total_sales=Count("id")
            )
            .order_by("-total_sales")[:5]
        )

        contacts_chart = (
            Contact.objects
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )

        sales_chart = (
            Sale.objects.filter(status="signed")
            .values("sale_date")
            .annotate(total=Count("id"))
            .order_by("sale_date")
        )

        today = timezone.now().date()

        start_date = today - timedelta(days=29)

        contacts_activity = (
            Contact.objects
            .filter(created_at__date__gte=start_date)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Count("id"))
        )

        sales_activity = (
            Sale.objects
            .filter(
                status="signed",
                sale_date__gte=start_date
            )
            .values("sale_date")
            .annotate(total=Count("id"))
            .order_by("sale_date")
        )

        tasks_activity = (
            Task.objects
            .filter(
                completed_at__date__gte=start_date
            )
            .annotate(day=TruncDate("completed_at"))
            .values("day")
            .annotate(total=Count("id"))
        )


                    ###Generar fráfica############################################


        contacts_map = defaultdict(int)
        sales_map = defaultdict(int)
        tasks_map = defaultdict(int)  

        for item in contacts_activity:
            contacts_map[
                item["day"].strftime("%d/%m")
            ] = item["total"]

        for item in sales_activity:
            sales_map[
                item["sale_date"].strftime("%d/%m")
            ] = item["total"]

        for item in tasks_activity:
            tasks_map[
                item["day"].strftime("%d/%m")
            ] = item["total"]

            #########Eje X###########33

        selected_days = int(
            request.GET.get("days", 30)
        )

        start_date = timezone.now().date() - timedelta(days=30)

        end_date = timezone.now().date()

        start_date = end_date - timedelta(
            days=selected_days - 1
        )

        for i in range(selected_days):

            day = start_date + timedelta(days=i)

            key = day.strftime("%d/%m")

            labels.append(key)

            contacts_data.append(
                contacts_map.get(key, 0)
            )

            sales_data.append(
                sales_map.get(key, 0)
            )

            tasks_data.append(
                tasks_map.get(key, 0)
            )


    contacts_growth, contacts_trend = growth(contacts_current, contacts_previous)

    sales_growth, sales_trend = growth(sales_current, sales_previous)

    revenue_growth, revenue_trend = growth(revenue_current, revenue_previous)

    return render(request, "dashboard/home.html", {
        "total_contacts": total_contacts,
        "total_tasks": total_tasks,
        "total_properties": total_properties,
        "pending_tasks": pending_tasks,
        "overdue_tasks": overdue_tasks,
        "latest_contacts": latest_contacts,
        "latest_tasks": latest_tasks,
        "upcoming_tasks": upcoming_tasks,
        "completed_tasks": completed_tasks,
        "recent_activities": recent_activities,
        "total_revenue": total_revenue,
        "completed_sales_count": completed_sales_count,
        "average_sale": average_sale,
        "total_commission": total_commission,

        "recent_sales": recent_sales,
        "top_agents": top_agents,

        ###Grafica###
        "activity_labels": json.dumps(labels),
        "contacts_data": json.dumps(contacts_data),
        "sales_data": json.dumps(sales_data),
        "tasks_data": json.dumps(tasks_data),
        "contacts_current": contacts_current,
        "contacts_growth": contacts_growth,
        "contacts_trend": contacts_trend,
        "selected_days": selected_days,

        "sales_current": sales_current,
        "sales_growth": sales_growth,
        "sales_trend": sales_trend,

        "revenue_current": revenue_current,
        "revenue_growth": revenue_growth,
        "revenue_trend": revenue_trend,


    })
