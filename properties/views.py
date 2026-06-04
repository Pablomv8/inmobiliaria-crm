from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from .models import Property
from .forms import PropertyForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse


from django.db.models import Q

from django.db.models import Q

@login_required
def property_list(request):

    properties = Property.objects.all()

    search = request.GET.get("search")
    status = request.GET.get("status")
    property_type = request.GET.get("type")
    city = request.GET.get("city")

    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    ordering = request.GET.get("ordering")

    # BUSCADOR
    if search:
        properties = properties.filter(
            Q(title__icontains=search) |
            Q(street__icontains=search) |
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

    # PRECIO MÍNIMO
    if min_price:
        properties = properties.filter(
            price__gte=min_price
        )

    # PRECIO MÁXIMO
    if max_price:
        properties = properties.filter(
            price__lte=max_price
        )

    # ORDENACIÓN
    ordering_options = {
        "recent": "-created_at",
        "oldest": "created_at",
        "price_asc": "price",
        "price_desc": "-price",
        "title": "title",
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
        }
    )


@login_required
def property_detail(request, pk):

    property = get_object_or_404(Property, pk=pk)

    return render(request, 'properties/detail.html', {
        'property': property
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

    property_obj.status = request.POST.get("status")

    property_obj.save()

    return JsonResponse({
        "success": True
    })