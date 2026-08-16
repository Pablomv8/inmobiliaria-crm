from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from .models import Property, Zone
from contacts.models import Contact
from .forms import PropertyCommentForm, PropertyForm, OwnerContactForm
from .timeline import build_property_timeline
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse


from django.db.models import Q

from django.db.models import Q

@login_required
def property_list(request):
    Property.refresh_aged_contact_statuses()

    properties = Property.objects.all()

    search = request.GET.get("search")
    status = request.GET.get("status")
    property_type = request.GET.get("type")
    city = request.GET.get("city")

    bedrooms = request.GET.get("bedrooms")
    bathrooms = request.GET.get("bathrooms")

    ordering = request.GET.get("ordering")

    zones = Zone.objects.all()
    selected_zone = request.GET.get("zone")

    if selected_zone:

        properties = properties.filter(
            zone_id=selected_zone
        )

    # BUSCADOR
    if search:
        properties = properties.filter(
            Q(street__icontains=search) |
            Q(number__icontains=search) |
            Q(city__icontains=search)
        )

    # ESTADO
    if status:
        properties = properties.filter(status=status)

    # TIPO
    if property_type:
        properties = properties.filter(
            property_type=property_type
        )

    # CIUDAD
    if city:
        properties = properties.filter(
            city__icontains=city
        )

    if bedrooms:
        properties = properties.filter(
            bedrooms__gte=bedrooms
        )

    if bathrooms:
        properties = properties.filter(
            bathrooms__gte=bathrooms
        )
    

    # ORDENACIÓN
    ordering_options = {
        "recent": "-created_at",
        "oldest": "created_at",
        "address": "street",
    }

    if ordering in ordering_options:
        properties = properties.order_by(
            ordering_options[ordering]
        )
    else:
        properties = properties.order_by("-created_at")

    return render(
        request,
        "properties/list.html",
        {
            "properties": properties,
            "zones": zones,
            "property_types": Property.PROPERTY_TYPE_CHOICES,
            "status_choices": Property.STATUS_CHOICES,
        }
    )


@login_required
def property_detail(request, pk):
    Property.refresh_aged_contact_statuses()
    property = get_object_or_404(Property, pk=pk)
    property.sync_status()

    owners = property.contacts.filter(
        contact_type="owner"
    )

    buyers = property.contacts.filter(
        contact_type="buyer"
    )

    return render(request, 'properties/detail.html', {
        'property': property,
        'comments': property.comments.select_related("user"),
        'comment_form': PropertyCommentForm(),
        'timeline': build_property_timeline(property, request.user),
    })



@login_required
def property_create(request):

    if request.method == 'POST':

        form = PropertyForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            form.save()

            return redirect('properties')

    else:

        form = PropertyForm()

    return render(request, 'properties/form.html', {
        'form': form,
        'title': 'Nuevo inmueble'
    })

@login_required
def property_update(request, pk):

    property = get_object_or_404(Property, pk=pk)

    if request.method == 'POST':

        form = PropertyForm(
            request.POST,
            request.FILES,
            instance=property
        )

        if form.is_valid():

            form.save()

            return redirect('property_detail', pk=property.id)

    else:

        form = PropertyForm(instance=property)

    return render(request, 'properties/form.html', {
        'form': form,
        'title': 'Editar inmueble'
    })

@login_required
def property_delete(request, pk):

    property = get_object_or_404(Property, pk=pk)

    if request.method == 'POST':

        property.delete()

        return redirect('properties')

    return render(request, 'properties/delete.html', {
        'property': property
    })


@login_required
@require_POST
def property_update_status(request, pk):

    property_obj = get_object_or_404(
        Property,
        pk=pk
    )

    property_obj.sync_status()

    return JsonResponse({
        "success": True,
        "status": property_obj.status,
        "status_display": property_obj.get_status_display(),
    })


@login_required
@require_POST
def property_add_comment(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)
    form = PropertyCommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.property = property_obj
        comment.user = request.user
        comment.save()
        return redirect("property_detail", pk=property_obj.pk)

    property_obj.sync_status()
    return render(
        request,
        "properties/detail.html",
        {
            "property": property_obj,
            "comments": property_obj.comments.select_related("user"),
            "comment_form": form,
            "timeline": build_property_timeline(property_obj, request.user),
        },
        status=400,
    )


@login_required
def add_owner_to_property(request, property_id):

    property_obj = get_object_or_404(Property, id=property_id)

    if request.method == "POST":

        contact = get_object_or_404(
            Contact,
            id=request.POST.get("contact_id")
        )

        # aseguramos tipo propietario
        contact.contact_type = "owner"
        contact.save()

        contact.properties.add(property_obj)

        return redirect("property_detail", property_obj.id)

    contacts = Contact.objects.filter(
        contact_type="owner"
    )

    return render(
        request,
        "properties/add_owner.html",
        {
            "property": property_obj,
            "contacts": contacts
        }
    )

@login_required
def create_owner_for_property(request, property_id):

    property_obj = get_object_or_404(Property, id=property_id)

    if request.method == "POST":

        form = OwnerContactForm(
            request.POST,
            property_obj=property_obj
        )

        if form.is_valid():

            form.save()

            return redirect(
                "property_detail",
                property_obj.id
            )

    else:

        form = OwnerContactForm(
            property_obj=property_obj
        )

    return render(
        request,
        "properties/owner_form.html",
        {
            "form": form,
            "property": property_obj
        }
    )
