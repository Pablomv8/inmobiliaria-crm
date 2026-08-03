from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .models import Listing
from calendar_app.models import Appointment
from users.models import User
from django.db.models import Q
from django.contrib import messages
from .forms import ListingForm

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
            Q(property__street__icontains=search) |
            Q(property__number__icontains=search) |
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
        "owner",
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
        get_user_listings(request.user).select_related(
            "property",
            "owner",
            "agent",
            "source_appointment__news",
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

    if (
        appointment.status != "completed"
        or not appointment.result_comment.strip()
    ):
        messages.warning(
            request,
            "Añade el comentario de resultado antes de crear el encargo.",
        )
        return redirect("appointment_detail", pk=appointment.pk)

    if appointment.news is None:
        messages.error(
            request,
            "La cita no tiene una noticia asociada.",
        )
        return redirect("appointment_detail", pk=appointment.pk)

    news = appointment.news
    property_obj = appointment.related_property

    # Evitar duplicados
    existing_listing = Listing.objects.filter(
    source_appointment=appointment
    ).first()

    if existing_listing:

        if appointment.result_success is not True:
            appointment.result_success = True
            appointment.save(update_fields=["result_success"])

        return redirect(
            "listing_detail",
            existing_listing.id
        )

    form = ListingForm(
        request.POST or None,
        property_obj=property_obj,
    )

    if request.method == "POST" and form.is_valid():
        listing = form.save(commit=False)
        listing.property = property_obj
        listing.listing_type = news.motivation
        listing.owner_price = news.client_price
        listing.agency_price = news.estimated_price
        listing.agent = request.user
        listing.source_appointment = appointment
        listing.status = "active"
        listing.price_diference = news.client_price - news.estimated_price
        listing.save()

        appointment.result_success = True
        appointment.save(update_fields=["result_success"])

        return redirect("listing_detail", listing_id=listing.pk)

    return render(
        request,
        "listings/form.html",
        {
            "form": form,
            "appointment": appointment,
            "news": news,
            "property": property_obj,
            "agent": request.user,
            "has_owners": form.fields["owner"].queryset.exists(),
        },
    )



