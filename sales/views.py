from django.views.generic import ListView
from django.views.generic import CreateView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.views.decorators.http import require_POST

from django.urls import reverse_lazy

from .models import RentalContract, Sale
from .forms import (
    RentalContractClosingForm,
    SaleClosingForm,
    SaleForm,
)

from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect

from activities.utils import log_activity

from django.db.models import Q
from users.models import User
from users.forms import AgentReassignmentForm
from users.permissions import can_manage_assignments
from config.pagination import paginate
from calendar_app.models import Appointment


@login_required
def sale_list(request):

    sales = Sale.objects.select_related(
        "related_property",
        "buyer",
        "agent"
    )

    search = request.GET.get("search")
    status = request.GET.get("status")
    agent = request.GET.get("agent")
    ordering = request.GET.get("ordering")

    if not (
        request.user.is_superuser
        or request.user.role in ["admin", "manager"]
    ):
        sales = sales.filter(agent=request.user)
        agent = str(request.user.pk)

    # BUSCADOR
    if search:

        sales = sales.filter(

            Q(related_property__street__icontains=search) |
            Q(related_property__number__icontains=search) |
            Q(related_property__city__icontains=search) |
            Q(buyer__name__icontains=search) |
            Q(agent__username__icontains=search)

        )

    # ESTADO
    if status:

        sales = sales.filter(status=status)

    # AGENTE
    if agent and (
        request.user.is_superuser
        or request.user.role in ["admin", "manager"]
    ):

        sales = sales.filter(agent_id=agent)

    # ORDEN
    ordering_options = {

        "date_desc": "-sale_date",
        "date_asc": "sale_date",

        "price_desc": "-sale_price",
        "price_asc": "sale_price",

    }

    if ordering in ordering_options:

        sales = sales.order_by(
            ordering_options[ordering]
        )

    else:

        sales = sales.order_by("-sale_date")

    sales = paginate(request, sales)

    return render(
        request,
        "sales/sale_list.html",
        {
            "sales": sales,
            "page_obj": sales,
            "status_choices": Sale.STATUS_CHOICES,
            "agents": User.objects.filter(
                role="agent"
            )
        }
    )

class SaleListView(ListView):

    model = Sale

    template_name = "sales/sale_list.html"

    context_object_name = "sales"

    ordering = ["-sale_date"]
    paginate_by = 15


class SaleCreateView(CreateView):

    model = Sale

    form_class = SaleForm

    template_name = "sales/sale_form.html"

    success_url = reverse_lazy("sale_list")

    @login_required
    def form_valid(self, form):

        response = super().form_valid(form)

        sale = self.object

        # contacto cerrado

        sale.buyer.status = "closed"
        sale.buyer.save()

        log_activity(
            self.request.user,
            "sale_created",
            f"Registró la venta de '{sale.related_property.full_address}'"
        )

        return response


def _contract_appointment_for_user(request, appointment_id):
    appointments = Appointment.objects.select_related(
        "listing__property",
        "listing__owner",
        "listing__agent",
        "order__buyer",
        "purchase_proposal__buyer",
        "purchase_proposal__listing__property",
        "purchase_proposal__listing__owner",
        "agent",
    ).filter(
        pk=appointment_id,
        appointment_type="contract",
    )
    if not (
        request.user.is_superuser
        or request.user.role in ["admin", "manager"]
    ):
        appointments = appointments.filter(agent=request.user)
    return get_object_or_404(appointments)


def _contract_relations(appointment):
    proposal = appointment.purchase_proposal
    listing = appointment.listing or (proposal.listing if proposal else None)
    client = (
        proposal.buyer
        if proposal
        else appointment.order.buyer
        if appointment.order_id
        else appointment.contact
    )
    return listing, client, proposal


@login_required
@require_POST
def contract_signing_decision(request, appointment_id):
    appointment = _contract_appointment_for_user(request, appointment_id)
    if appointment.status != "completed" or not appointment.result_comment.strip():
        messages.warning(
            request,
            "Completa la cita y añade su comentario antes de registrar la firma.",
        )
        return redirect("appointment_detail", pk=appointment.pk)

    signed = request.POST.get("signed")
    if signed not in ["yes", "no"]:
        messages.error(request, "Indica si el contrato se ha firmado.")
        return redirect("appointment_detail", pk=appointment.pk)

    appointment.result_success = signed == "yes"
    appointment.save(update_fields=["result_success"])

    if signed == "no":
        messages.info(request, "Se ha registrado que el contrato no se firmó.")
        return redirect("appointment_detail", pk=appointment.pk)

    if hasattr(appointment, "completed_sale"):
        return redirect("sale_detail", pk=appointment.completed_sale.pk)
    if hasattr(appointment, "completed_rental_contract"):
        return redirect(
            "rental_contract_detail",
            pk=appointment.completed_rental_contract.pk,
        )

    return redirect("create_closing_from_contract", appointment_id=appointment.pk)


@login_required
def create_closing_from_contract(request, appointment_id):
    appointment = _contract_appointment_for_user(request, appointment_id)
    if (
        appointment.status != "completed"
        or not appointment.result_comment.strip()
        or appointment.result_success is not True
    ):
        messages.warning(
            request,
            "Confirma primero que el contrato se ha firmado.",
        )
        return redirect("appointment_detail", pk=appointment.pk)

    if hasattr(appointment, "completed_sale"):
        return redirect("sale_detail", pk=appointment.completed_sale.pk)
    if hasattr(appointment, "completed_rental_contract"):
        return redirect(
            "rental_contract_detail",
            pk=appointment.completed_rental_contract.pk,
        )

    listing, client, proposal = _contract_relations(appointment)
    if listing is None or client is None:
        messages.error(
            request,
            "La cita no tiene un encargo y un cliente válidos para cerrar la operación.",
        )
        return redirect("appointment_detail", pk=appointment.pk)

    is_sale = listing.listing_type == "sale"
    form_class = SaleClosingForm if is_sale else RentalContractClosingForm
    form = form_class(
        request.POST or None,
        appointment=appointment,
    )

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            locked_appointment = Appointment.objects.select_for_update().get(
                pk=appointment.pk
            )
            locked_listing = listing.__class__.objects.select_for_update().select_related(
                "property",
                "owner",
            ).get(pk=listing.pk)
            property_obj = locked_listing.property
            owner = locked_listing.owner
            agent = locked_appointment.agent or request.user

            if is_sale:
                sale = form.save(commit=False)
                sale.related_property = property_obj
                sale.listing = locked_listing
                sale.order = locked_appointment.order
                sale.proposal = proposal
                sale.source_contract_appointment = locked_appointment
                sale.former_owner = owner
                sale.buyer = client
                sale.agent = agent
                sale.sale_date = timezone.localdate()
                sale.status = "signed"
                sale.commission_amount = (
                    sale.seller_commission + sale.buyer_commission
                )
                sale.save()

                if owner and owner.pk != client.pk:
                    property_obj.contacts.remove(owner)
                property_obj.contacts.add(client)
                if client.contact_type != "owner":
                    client.contact_type = "owner"
                    client.save(update_fields=["contact_type"])

                locked_listing.status = "sold"
                locked_listing.workflow_status = "closed"
                locked_listing.save(update_fields=["status", "workflow_status"])
                property_obj.occupied_by = "owner"
                property_obj.save(update_fields=["occupied_by", "status"])
                closing = sale
                detail_name = "sale_detail"
                description = f"Registró la compraventa de '{property_obj.full_address}'"
            else:
                if owner is None:
                    form.add_error(
                        None,
                        "El encargo necesita un propietario para registrar el alquiler.",
                    )
                    return render(
                        request,
                        "sales/contract_closing_form.html",
                        {
                            "form": form,
                            "appointment": appointment,
                            "listing": listing,
                            "client": client,
                            "is_sale": is_sale,
                            "contract_date": timezone.localdate(),
                        },
                        status=400,
                    )
                rental = form.save(commit=False)
                rental.related_property = property_obj
                rental.listing = locked_listing
                rental.order = locked_appointment.order
                rental.proposal = proposal
                rental.source_contract_appointment = locked_appointment
                rental.tenant = client
                rental.owner = owner
                rental.agent = agent
                rental.contract_date = timezone.localdate()
                rental.status = "signed"
                rental.save()
                property_obj.contacts.add(client)

                locked_listing.status = "rented"
                locked_listing.workflow_status = "closed"
                locked_listing.save(update_fields=["status", "workflow_status"])
                property_obj.occupied_by = "tenants"
                property_obj.save(update_fields=["occupied_by", "status"])
                closing = rental
                detail_name = "rental_contract_detail"
                description = f"Registró el alquiler de '{property_obj.full_address}'"

            if locked_appointment.order_id:
                locked_appointment.order.__class__.objects.filter(
                    pk=locked_appointment.order_id,
                ).update(status="closed")

            log_activity(
                request.user,
                "sale_created" if is_sale else "rental_created",
                description,
            )

        messages.success(
            request,
            "Compraventa registrada y titularidad transferida."
            if is_sale
            else "Contrato de alquiler registrado correctamente.",
        )
        return redirect(detail_name, pk=closing.pk)

    return render(
        request,
        "sales/contract_closing_form.html",
        {
            "form": form,
            "appointment": appointment,
            "listing": listing,
            "client": client,
            "proposal": proposal,
            "is_sale": is_sale,
            "contract_date": timezone.localdate(),
        },
    )


@login_required
def sale_detail(request, pk):
    sales = Sale.objects.select_related(
        "related_property",
        "buyer",
        "former_owner",
        "agent",
        "listing",
        "order",
        "proposal",
        "source_contract_appointment",
    )
    if not (
        request.user.is_superuser
        or request.user.role in ["admin", "manager"]
    ):
        sales = sales.filter(agent=request.user)
    return render(
        request,
        "sales/sale_detail.html",
        {"sale": get_object_or_404(sales, pk=pk)},
    )


@login_required
def sale_reassign(request, pk):
    if not can_manage_assignments(request.user):
        raise PermissionDenied

    sale = get_object_or_404(
        Sale.objects.select_related("related_property", "buyer", "agent"),
        pk=pk,
    )
    form = AgentReassignmentForm(
        request.POST or None,
        current_agent=sale.agent,
    )
    if request.method == "POST" and form.is_valid():
        sale.agent = form.cleaned_data["agent"]
        sale.save(update_fields=["agent"])
        messages.success(request, "La venta se ha reasignado correctamente.")
        return redirect("sale_detail", pk=sale.pk)

    return render(
        request,
        "users/reassign_agent.html",
        {
            "form": form,
            "object_type": "venta",
            "object_label": f"{sale.related_property.full_address} · {sale.buyer}",
            "return_url": reverse_lazy("sale_detail", args=[sale.pk]),
        },
    )
@login_required
def rental_contract_list(request):
    contracts = RentalContract.objects.select_related(
        "related_property",
        "tenant",
        "owner",
        "agent",
    )

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "")
    agent = request.GET.get("agent", "")
    ordering = request.GET.get("ordering", "date_desc")

    if not (
        request.user.is_superuser
        or request.user.role in ["admin", "manager"]
    ):
        contracts = contracts.filter(agent=request.user)
        agent = str(request.user.pk)

    if search:
        contracts = contracts.filter(
            Q(related_property__street__icontains=search)
            | Q(related_property__number__icontains=search)
            | Q(related_property__city__icontains=search)
            | Q(tenant__name__icontains=search)
            | Q(owner__name__icontains=search)
            | Q(agent__username__icontains=search)
            | Q(contract_reference__icontains=search)
        )

    if status:
        contracts = contracts.filter(status=status)

    if agent and (
        request.user.is_superuser
        or request.user.role in ["admin", "manager"]
    ):
        contracts = contracts.filter(agent_id=agent)

    ordering_options = {
        "date_desc": "-contract_date",
        "date_asc": "contract_date",
        "price_desc": "-rent_price",
        "price_asc": "rent_price",
    }
    contracts = contracts.order_by(
        ordering_options.get(ordering, "-contract_date")
    )

    contracts = paginate(request, contracts)
    return render(
        request,
        "sales/rental_contract_list.html",
        {
            "contracts": contracts,
            "page_obj": contracts,
            "status_choices": RentalContract.STATUS_CHOICES,
            "agents": User.objects.filter(role="agent").order_by("username"),
        },
    )


@login_required
def rental_contract_detail(request, pk):
    contracts = RentalContract.objects.select_related(
        "related_property",
        "tenant",
        "owner",
        "agent",
        "listing",
        "order",
        "proposal",
        "source_contract_appointment",
    )
    if not (
        request.user.is_superuser
        or request.user.role in ["admin", "manager"]
    ):
        contracts = contracts.filter(agent=request.user)
    return render(
        request,
        "sales/rental_contract_detail.html",
        {"contract": get_object_or_404(contracts, pk=pk)},
    )


@login_required
def rental_contract_reassign(request, pk):
    if not can_manage_assignments(request.user):
        raise PermissionDenied

    contract = get_object_or_404(
        RentalContract.objects.select_related(
            "related_property",
            "tenant",
            "agent",
        ),
        pk=pk,
    )
    form = AgentReassignmentForm(
        request.POST or None,
        current_agent=contract.agent,
    )
    if request.method == "POST" and form.is_valid():
        contract.agent = form.cleaned_data["agent"]
        contract.save(update_fields=["agent"])
        messages.success(request, "El alquiler se ha reasignado correctamente.")
        return redirect("rental_contract_detail", pk=contract.pk)

    return render(
        request,
        "users/reassign_agent.html",
        {
            "form": form,
            "object_type": "alquiler",
            "object_label": (
                f"{contract.related_property.full_address} · {contract.tenant}"
            ),
            "return_url": reverse_lazy(
                "rental_contract_detail",
                args=[contract.pk],
            ),
        },
    )
@require_POST
@login_required
def sale_update_status(request, pk):

    sale = get_object_or_404(Sale, pk=pk)

    sale.status = request.POST.get("status")
    sale.save()  # aquí se ejecuta la lógica del modelo

    return redirect("sale_list")
