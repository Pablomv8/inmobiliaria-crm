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
from django.contrib import messages
from django.apps import apps
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from config.pagination import paginate
from users.permissions import (
    assignable_agents,
    can_manage_office,
    has_related_records,
    require_object_management,
    scope_to_user,
)
from news.models import News


from django.db.models import Q
from .geocoding import geocode_address, is_arcos_de_la_frontera

ADDRESS_FIELDS = {"street", "number", "postal_code", "city", "province"}
COORDINATE_FIELDS = {"latitude", "longitude"}


def property_form_context(form, title):
    return {
        "form": form,
        "title": title,
    }


@login_required
@require_GET
def property_address_suggestions(request):
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"suggestions": []})

    Street = apps.get_model("tasks", "Street")
    streets = Street.objects.filter(
        municipality="Arcos de la Frontera",
        name__icontains=query,
    ).order_by("name")[:8]
    return JsonResponse({
        "suggestions": [
            {
                "label": street.name,
                "street": street.name,
                "city": street.municipality,
                "province": "Cádiz",
            }
            for street in streets
        ],
    })


def apply_automatic_geocoding(form, property_obj, creating=False):
    address_changed = bool(ADDRESS_FIELDS.intersection(form.changed_data))
    coordinates_changed = bool(COORDINATE_FIELDS.intersection(form.changed_data))
    submitted_coordinates = (
        property_obj.latitude is not None
        and property_obj.longitude is not None
    )
    manually_positioned = coordinates_changed and submitted_coordinates

    if address_changed and not manually_positioned:
        property_obj.latitude = None
        property_obj.longitude = None

    has_coordinates = (
        property_obj.latitude is not None
        and property_obj.longitude is not None
    )
    should_geocode = (
        (creating or address_changed)
        and not manually_positioned
        and not has_coordinates
        and is_arcos_de_la_frontera(property_obj.city)
    )
    if not should_geocode:
        return None

    result = geocode_address(
        property_obj.street,
        property_obj.number,
        property_obj.postal_code,
        property_obj.city,
        property_obj.province,
    )
    if result:
        property_obj.latitude = result.latitude
        property_obj.longitude = result.longitude
    return result


@login_required
def property_list(request):
    Property.refresh_aged_contact_statuses()

    properties = Property.objects.filter(is_archived=False).select_related(
        "assigned_agent",
        "zone",
    )

    search = request.GET.get("search")
    status = request.GET.get("status")
    property_type = request.GET.get("type")
    city = request.GET.get("city")
    agent = request.GET.get("agent")

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

    if agent and can_manage_office(request.user):
        properties = properties.filter(assigned_agent_id=agent)

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

    properties = paginate(request, properties)

    return render(
        request,
        "properties/list.html",
        {
            "properties": properties,
            "page_obj": properties,
            "zones": zones,
            "property_types": Property.PROPERTY_TYPE_CHOICES,
            "status_choices": Property.STATUS_CHOICES,
            "agents": (
                assignable_agents()
                if can_manage_office(request.user)
                else ()
            ),
        }
    )


@login_required
def property_detail(request, pk):
    Property.refresh_aged_contact_statuses()
    property = get_object_or_404(Property, pk=pk)
    property.sync_status()

    owners = property.contacts.filter(
        is_owner=True
    )

    buyers = property.contacts.filter(
        is_buyer=True
    )
    news_items = scope_to_user(
        News.objects.filter(related_property=property).select_related("agent"),
        request.user,
    )
    comments = property.comments.select_related("user")
    if not can_manage_office(request.user) and property.assigned_agent_id != request.user.pk:
        comments = comments.none()

    return render(request, 'properties/detail.html', {
        'property': property,
        'owners': owners,
        'comments': comments,
        'comment_form': PropertyCommentForm(),
        'timeline': build_property_timeline(property, request.user),
        'news_items': news_items,
    })



@login_required
def property_create(request):

    if request.method == 'POST':

        form = PropertyForm(
            request.POST,
            request.FILES,
            user=request.user,
        )

        if form.is_valid():

            property_obj = form.save(commit=False)
            property_obj.created_by = request.user
            if "assigned_agent" not in form.fields:
                property_obj.assigned_agent = request.user
            geocoding_result = apply_automatic_geocoding(
                form,
                property_obj,
                creating=True,
            )
            property_obj.save()
            form.save_m2m()

            if geocoding_result:
                messages.success(
                    request,
                    "Inmueble localizado automáticamente en el mapa.",
                )
            elif (
                property_obj.latitude is None
                and is_arcos_de_la_frontera(property_obj.city)
            ):
                messages.warning(
                    request,
                    "El inmueble se ha guardado, pero no se pudo localizar "
                    "automáticamente. Puedes corregir el punto al editarlo.",
                )

            return redirect('properties')

    else:

        form = PropertyForm(user=request.user)

    return render(
        request,
        'properties/form.html',
        property_form_context(form, 'Nuevo inmueble'),
    )


@login_required
def property_map(request):
    Property.refresh_aged_contact_statuses()
    all_properties = Property.objects.filter(is_archived=False)
    properties = all_properties.filter(
        latitude__isnull=False,
        longitude__isnull=False,
    ).select_related("zone")

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "")
    property_type = request.GET.get("type", "")
    zone = request.GET.get("zone", "")
    occupied_by = request.GET.get("occupied_by", "")

    if search:
        properties = properties.filter(
            Q(street__icontains=search)
            | Q(number__icontains=search)
            | Q(city__icontains=search)
        )
    if status:
        properties = properties.filter(status=status)
    if property_type:
        properties = properties.filter(property_type=property_type)
    if zone:
        properties = properties.filter(zone_id=zone)
    if occupied_by:
        properties = properties.filter(occupied_by=occupied_by)

    properties = list(properties.order_by("street", "number"))
    property_map_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": str(property_obj.pk),
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(property_obj.longitude),
                        float(property_obj.latitude),
                    ],
                },
                "properties": {
                    "id": str(property_obj.pk),
                    "address": property_obj.full_address,
                    "status": property_obj.status,
                    "status_label": property_obj.get_status_display(),
                    "property_type": property_obj.get_property_type_display(),
                    "occupied_by": property_obj.get_occupied_by_display(),
                    "zone": str(property_obj.zone or "Sin zona"),
                    "detail_url": reverse("property_detail", args=[property_obj.pk]),
                },
            }
            for property_obj in properties
        ],
    }
    geolocated_total = all_properties.filter(
        latitude__isnull=False,
        longitude__isnull=False,
    ).count()

    return render(
        request,
        "properties/map.html",
        {
            "properties": properties,
            "property_map_data": property_map_data,
            "displayed_count": len(properties),
            "geolocated_total": geolocated_total,
            "pending_location_count": all_properties.count() - geolocated_total,
            "zones": Zone.objects.order_by("name"),
            "property_types": Property.PROPERTY_TYPE_CHOICES,
            "status_choices": Property.STATUS_CHOICES,
            "occupancy_choices": Property.OCCUPANCY_CHOICES,
        },
    )

@login_required
def property_update(request, pk):

    property = get_object_or_404(Property, pk=pk, is_archived=False)
    require_object_management(request.user, property, "assigned_agent")

    if request.method == 'POST':

        form = PropertyForm(
            request.POST,
            request.FILES,
            instance=property,
            user=request.user,
        )

        if form.is_valid():
            property_obj = form.save(commit=False)
            geocoding_result = apply_automatic_geocoding(form, property_obj)
            property_obj.save()
            form.save_m2m()

            if geocoding_result:
                messages.success(
                    request,
                    "Dirección actualizada y localizada automáticamente.",
                )
            elif (
                ADDRESS_FIELDS.intersection(form.changed_data)
                and property_obj.latitude is None
                and is_arcos_de_la_frontera(property_obj.city)
            ):
                messages.warning(
                    request,
                    "La dirección se ha actualizado, pero no se pudo localizar. "
                    "Puedes seleccionar el punto manualmente en el mapa.",
                )

            return redirect('property_detail', pk=property.id)

    else:

        form = PropertyForm(instance=property, user=request.user)

    return render(
        request,
        'properties/form.html',
        property_form_context(form, 'Editar inmueble'),
    )


@login_required
@require_POST
def property_geocode(request):
    city = request.POST.get("city", "")
    if not is_arcos_de_la_frontera(city):
        return JsonResponse(
            {
                "success": False,
                "message": "La localización automática está configurada para Arcos de la Frontera.",
            },
            status=400,
        )

    result = geocode_address(
        request.POST.get("street", ""),
        request.POST.get("number", ""),
        request.POST.get("postal_code", ""),
        city,
        request.POST.get("province", ""),
    )
    if not result:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "No se encontró la dirección. Pulsa sobre el mapa para "
                    "colocar el inmueble manualmente."
                ),
            },
            status=404,
        )

    return JsonResponse({
        "success": True,
        "latitude": str(result.latitude),
        "longitude": str(result.longitude),
        "source": result.source,
        "label": result.label,
    })

@login_required
def property_delete(request, pk):

    property = get_object_or_404(Property, pk=pk, is_archived=False)
    require_object_management(request.user, property, "assigned_agent")

    will_archive = (
        not can_manage_office(request.user)
        or has_related_records(property)
    )

    if request.method == 'POST':

        if will_archive:
            property.is_archived = True
            property.archived_at = timezone.now()
            property.save(update_fields=["is_archived", "archived_at", "status"])
            messages.success(
                request,
                "El inmueble se ha archivado sin perder su historial.",
            )
        else:
            property.delete()
            messages.success(request, "El inmueble se ha eliminado definitivamente.")

        return redirect('properties')

    return render(request, 'properties/delete.html', {
        'property': property,
        'will_archive': will_archive,
    })


@login_required
@require_POST
def property_update_status(request, pk):

    property_obj = get_object_or_404(
        Property,
        pk=pk,
        is_archived=False,
    )
    require_object_management(request.user, property_obj, "assigned_agent")

    property_obj.sync_status()

    return JsonResponse({
        "success": True,
        "status": property_obj.status,
        "status_display": property_obj.get_status_display(),
    })


@login_required
@require_POST
def property_add_comment(request, pk):
    property_obj = get_object_or_404(Property, pk=pk, is_archived=False)
    require_object_management(request.user, property_obj, "assigned_agent")
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

    property_obj = get_object_or_404(Property, id=property_id, is_archived=False)
    require_object_management(request.user, property_obj, "assigned_agent")

    if request.method == "POST":

        contact = get_object_or_404(
            Contact,
            id=request.POST.get("contact_id")
        )

        # Añadimos el rol sin retirar su posible rol de comprador.
        if not contact.is_owner:
            contact.is_owner = True
            contact.save(update_fields=["is_owner"])

        contact.properties.add(property_obj)

        return redirect("property_detail", property_obj.id)

    contacts = Contact.objects.filter(
        is_owner=True,
        is_archived=False,
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

    property_obj = get_object_or_404(Property, id=property_id, is_archived=False)
    require_object_management(request.user, property_obj, "assigned_agent")

    if request.method == "POST":

        form = OwnerContactForm(
            request.POST,
            property_obj=property_obj,
            user=request.user,
        )

        if form.is_valid():

            form.save()

            return redirect(
                "property_detail",
                property_obj.id
            )

    else:

        form = OwnerContactForm(
            property_obj=property_obj,
            user=request.user,
        )

    return render(
        request,
        "properties/owner_form.html",
        {
            "form": form,
            "property": property_obj
        }
    )
