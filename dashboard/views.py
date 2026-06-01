from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

from contacts.models import Contact
from properties.models import Property
from tasks.models import Task
from activities.models import Activity

def home(request):
    return render(request, 'dashboard/home.html')

@login_required
def dashboard(request):

    user = request.user

    if user.role in ["admin", "manager"]:

        contacts = Contact.objects.all()
        tasks = Task.objects.all()

        total_properties = Property.objects.count()

        recent_activities = Activity.objects.all()[:6]

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

    total_contacts = contacts.count()

    total_tasks = tasks.count()

    pending_tasks = tasks.filter(
        status="pending"
    ).count()

    overdue_tasks = tasks.filter(
        status__in=["pending", "in_progress"],
        due_date__lt=timezone.now()
    ).count()

    contacts_by_status = contacts.values(
        "status"
    ).annotate(
        total=Count("id")
    )

    latest_contacts = contacts.order_by(
        "-created_at"
    )[:5]

    latest_tasks = tasks.order_by(
        "-created_at"
    )[:5]

    upcoming_tasks = tasks.filter(
        due_date__isnull=False,
        due_date__gte=timezone.now()
    ).order_by("due_date")[:5]

    completed_tasks = tasks.filter(
        status="done"
    ).order_by("-updated_at")[:5]

    

    return render(request, "dashboard/home.html", {
        "total_contacts": total_contacts,
        "total_tasks": total_tasks,
        "total_properties": total_properties,
        "pending_tasks": pending_tasks,
        "overdue_tasks": overdue_tasks,
        "contacts_by_status": contacts_by_status,
        "latest_contacts": latest_contacts,
        "latest_tasks": latest_tasks,
        "upcoming_tasks": upcoming_tasks,
        "completed_tasks": completed_tasks,
        "recent_activities": recent_activities,
    })