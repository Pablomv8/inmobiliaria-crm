from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone


from django.contrib.auth.decorators import login_required
from .models import Listing
from calendar_app.models import Appointment
from users.models import User
from django.db.models import Q

def get_user_listings(user):

    if (
        user.is_superuser
        or user.role in ["admin", "manager"]
    ):
        return Listing.objects.all()

    return Listing.objects.filter(
        agent=user
    )

@login_required
def listing_list(request):

    # BASE QUERYSET SEGÚN PERMISOS
    if request.user.role in ["admin", "manager"]:

        listings = Listing.objects.all()

    else:

        listings = Listing.objects.filter(
            agent=request.user
        )

    # ------------------------
    # SEARCH
    # ------------------------
    search = request.GET.get("search")

    if search:

        listings = listings.filter(
            Q(property__title__icontains=search) |
            Q(property__street__icontains=search) |
            Q(property__city__icontains=search)
        )

    # ------------------------
    # STATUS
    # ------------------------
    status = request.GET.get("status")

    if status:

        listings = listings.filter(
            status=status
        )

    # ------------------------
    # TYPE
    # ------------------------
    listing_type = request.GET.get("listing_type")

    if listing_type:

        listings = listings.filter(
            listing_type=listing_type
        )

    # ------------------------
    # AGENT (solo managers/admin)
    # ------------------------
    agent = request.GET.get("agent")

    if (
        agent
        and request.user.role in ["admin", "manager"]
    ):

        listings = listings.filter(
            agent_id=agent
        )

    # ------------------------
    # FINAL QUERYSET
    # ------------------------
    listings = listings.select_related(
        "property",
        "agent",
        "source_appointment"
    ).order_by(
        "-created_at"
    )

    # ------------------------
    # CONTEXT
    # ------------------------
    context = {

        "listings": listings,

        "status_choices": Listing.STATUS_CHOICES,
        "type_choices": Listing.TYPE_CHOICES,
        "agents": User.objects.filter(
            role="agent"
        )
    }

    return render(
        request,
        "listings/list.html",
        context
    )
@login_required
def listing_detail(request, listing_id):

    listing = get_object_or_404(
        get_user_listings(request.user),
        id=listing_id
    )

    return render(
        request,
        "listings/detail.html",
        {
            "listing": listing
        }
    )

@login_required
def create_listing_from_appointment(request, appointment_id):

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        agent=request.user
    )

    news = appointment.news
    property = appointment.related_property

    # Evitar duplicados
    existing_listing = Listing.objects.filter(
    source_appointment=appointment
    ).first()

    if existing_listing:

        return redirect(
            "listing_detail",
            existing_listing.id
        )

    listing = Listing.objects.create(

        property=property,

        listing_type=news.motivation,  # venta / alquiler

        owner_price=news.client_price,

        agency_price=news.estimated_price,

        agent=request.user,

        source_appointment=appointment,

        status="active",

        price_diference = news.client_price - news.estimated_price,

        start_date=timezone.now().date(),
    )


    return redirect(
        "listing_detail",
        listing.id
    )



