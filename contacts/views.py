from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model

from .models import Contact
from .forms import ContactForm

from activities.utils import log_activity


User = get_user_model()
# Create your views here.
@login_required
def contact_list(request):

    contacts = Contact.objects.select_related('assigned_agent') \
        .prefetch_related('properties')

    search = request.GET.get("search")
    status = request.GET.get("status")
    agent = request.GET.get("agent")
    ordering = request.GET.get("ordering")

    # 🔍 SEARCH
    if search:
        contacts = contacts.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )

    # 🎯 STATUS
    if status:
        contacts = contacts.filter(status=status)

    # 👤 AGENTE
    if agent:
        contacts = contacts.filter(assigned_agent_id=agent)

    # ↕ ORDENACIÓN
    if ordering:
        contacts = contacts.order_by(ordering)
    else:
        contacts = contacts.order_by("-created_at")

    return render(request, "contacts/list.html", {
        "contacts": contacts,
        "agents": User.objects.filter(role="agent")
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

            contact = form.save()

            log_activity(
                request.user,
                "contact_created",
                f"Creó el contacto {contact.name}"
            )

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

            contact = form.save()

            log_activity(
                request.user,
                "contact_updated",
                f"Editó el contacto {contact.name}"
            )

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
        name = contact.name

        log_activity(
            request.user,
            "contact_deleted",
            f"Eliminó el contacto {name}"
        )
        

        return redirect('contact_list')

    return render(request, 'contacts/delete.html', {
        'contact': contact
    })
    

@require_POST
@login_required
def contact_update_status(request, pk):

    contact = get_object_or_404(Contact, pk=pk)

    if request.user.role == "agent" and contact.assigned_agent != request.user:
        return JsonResponse({"success": False}, status=403)

    status = request.POST.get("status")

    if status in dict(Contact.STATUS_CHOICES):
        contact.status = status
        contact.save()

        return JsonResponse({
            "success": True,
            "status": contact.status
        })

    return JsonResponse({"success": False}, status=400)



@require_POST
@login_required
def contact_assign_agent(request, pk):

    contact = get_object_or_404(Contact, pk=pk)

    # seguridad básica
    if request.user.role == "agent":
        return JsonResponse({"success": False}, status=403)

    agent_id = request.POST.get("agent_id")

    agent = User.objects.filter(id=agent_id, role="agent").first()

    if not agent:
        return JsonResponse({"success": False}, status=400)

    contact.assigned_agent = agent
    
    contact.save()
    log_activity(
        request.user,
        "contact_assigned",
        f"Asignó el contacto '{contact.name}' a {agent.username}"
    )

    return JsonResponse({
        "success": True,
        "agent": agent.username
    })