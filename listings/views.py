from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone


from django.contrib.auth.decorators import login_required
from .models import Listing
from calendar_app.models import Appointment

@login_required
def listing_list(request):

    listings = Listing.objects.select_related(
        "property",
        "agent"
    ).order_by(
        "-created_at"
    )

    return render(
        request,
        "listings/list.html",
        {
            "listings": listings
        }
    )


@login_required
def listing_detail(request, listing_id):

    listing = get_object_or_404(
        Listing.objects.select_related(
            "property",
            "agent",
            "source_appointment"
        ),
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



