from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import Contact
from .forms import ContactForm

# Create your views here.
@login_required
def contact_list(request):

    contacts= Contact.objects.prefetch_related('properties')

    return render(request, 'contacts/list.html', {
        'contacts': contacts
    })

@login_required
def contact_detail(request, pk):

    contact = get_object_or_404(Contact, pk=pk)

    return render(request, 'contacts/detail.html', {
        'contact': contact
    })

@login_required
def contact_create(request):

    if request.method == 'POST':

        form = ContactForm(request.POST)

        if form.is_valid():

            form.save()

            return redirect('contact_list')

    else:

        form = ContactForm()

    return render(request, 'contacts/form.html', {
        'form': form,
        'title': 'Nuevo contacto'
    })

@login_required
def contact_update(request, pk):

    contact = get_object_or_404(Contact, pk=pk)

    if request.method == 'POST':

        form = ContactForm(request.POST, instance=contact)

        if form.is_valid():

            form.save()

            return redirect('contact_list')

    else:

        form = ContactForm(instance=contact)

    return render(request, 'contacts/form.html', {
        'form': form,
        'title': 'Editar contacto'
    })

@login_required
def contact_delete(request, pk):

    contact = get_object_or_404(Contact, pk=pk)

    if request.method == 'POST':

        contact.delete()

        return redirect('contacts')

    return render(request, 'contacts/delete.html', {
        'contact': contact
    })
    