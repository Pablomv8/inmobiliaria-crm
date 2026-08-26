from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model

from .models import Contact
from .forms import ContactForm
from activities.models import Activity
from listings.models import Listing
from news.models import News
from orders.models import Order
from sales.models import RentalContract, Sale

from activities.utils import log_activity
from config.pagination import paginate
from users.permissions import assignable_agents, can_manage_assignments


User = get_user_model()
# Create your views here.
@login_required
def contact_list(request):

    contacts = Contact.objects.select_related(
        "assigned_agent",
    ).prefetch_related("properties")

    search = request.GET.get("search", "").strip()
    role = request.GET.get("role", "")
    agent = request.GET.get("agent", "")
    ordering = request.GET.get("ordering", "")

    if search:
        contacts = contacts.filter(
            Q(name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(phone__icontains=search)
            | Q(email__icontains=search)
            | Q(identification_number__icontains=search)
            | Q(city__icontains=search)
        )

    role_filters = {
        "owner": {"is_owner": True},
        "buyer": {"is_buyer": True},
        "both": {"is_owner": True, "is_buyer": True},
    }
    if role in role_filters:
        contacts = contacts.filter(**role_filters[role])

    if agent:
        contacts = contacts.filter(assigned_agent_id=agent)

    ordering_options = {
        "oldest": "created_at",
        "name": "name",
        "city": "city",
    }
    contacts = contacts.order_by(ordering_options.get(ordering, "-created_at"))
    contacts = paginate(request, contacts)

    return render(request, "contacts/list.html", {
        "contacts": contacts,
        "page_obj": contacts,
        "agents": assignable_agents(),
        "role_choices": [
            ("owner", "Propietarios"),
            ("buyer", "Compradores"),
            ("both", "Ambos roles"),
        ],
    })

@login_required
def contact_create(request):

    if request.method == 'POST':

        form = ContactForm(request.POST, user=request.user)

        if form.is_valid():

            contact = form.save()

            log_activity(
                request.user,
                "contact_created",
                f"Creó el contacto {contact.name}",
                contact=contact
            )

            return redirect('contact_list')

    else:

        form = ContactForm(user=request.user)

    return render(request, 'contacts/form.html', {
        'form': form,
        'title': 'Nuevo contacto'
    })

@login_required
def contact_update(request, pk):

    contact = get_object_or_404(Contact, pk=pk)

    if request.method == 'POST':

        form = ContactForm(request.POST, instance=contact, user=request.user)

        if form.is_valid():

            contact = form.save()

            log_activity(
                request.user,
                "contact_updated",
                f"Editó el contacto {contact.name}",
                contact=contact
            )

            return redirect('contact_list')

    else:

        form = ContactForm(instance=contact, user=request.user)

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
            f"Eliminó el contacto {name}",
            contact=contact
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

        log_activity(
                request.user,
                "contact_updated",
                f"Editó el contacto {contact.name}",
                contact=contact
            )

        return JsonResponse({
            "success": True,
            "status": contact.status
        })

    return JsonResponse({"success": False}, status=400)



@require_POST
@login_required
def contact_assign_agent(request, pk):

    contact = get_object_or_404(Contact, pk=pk)

    if not can_manage_assignments(request.user):
        return JsonResponse({"success": False}, status=403)

    agent_id = request.POST.get("agent_id")

    agent = assignable_agents().filter(id=agent_id).first()

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


@login_required
def contact_detail(request, pk):

    contact = get_object_or_404(
        Contact,
        pk=pk
    )

    activities = Activity.objects.filter(
        contact=contact
    ).select_related(
        "user"
    )[:20]

    news_items = News.objects.none()
    listings = Listing.objects.none()
    orders = Order.objects.none()

    if contact.is_owner:
        news_items = News.objects.filter(
            related_property__contacts=contact,
        ).select_related(
            "related_property",
            "agent",
        ).distinct().order_by("-created_at")
        listings = Listing.objects.filter(
            Q(owner=contact) | Q(property__contacts=contact),
        ).select_related(
            "property",
            "owner",
            "agent",
        ).distinct().order_by("-created_at")
    if contact.is_buyer:
        orders = Order.objects.filter(buyer=contact).select_related(
            "zone",
            "agent",
        ).order_by("-created_at")

    completed_sales = Sale.objects.filter(
        Q(buyer=contact) | Q(former_owner=contact),
    ).select_related("related_property", "buyer", "former_owner").distinct()
    rental_contracts = RentalContract.objects.filter(
        Q(tenant=contact) | Q(owner=contact),
    ).select_related("related_property", "tenant", "owner").distinct()

    return render(
        request,
        "contacts/detail.html",
        {
            "contact": contact,
            "activities": activities,
            "news_items": news_items,
            "listings": listings,
            "orders": orders,
            "completed_sales": completed_sales,
            "rental_contracts": rental_contracts,
        }
    )
