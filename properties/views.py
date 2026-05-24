from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from .models import Property
from .forms import PropertyForm
from django.contrib.auth.decorators import login_required

@login_required
def property_list(request):

    properties = Property.objects.all()

    return render(request, 'properties/list.html', {
        'properties': properties
    })

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