from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.urls import reverse

from .models import Appointment, Call, CounterOffer, ProposalAppointment
from .forms import (
    AppointmentForm,
    AppointmentResultForm,
    CallForm,
    CallCommentForm,
    CounterOfferForm,
    ProposalAppointmentForm,
    SaleAppointmentForm,
)
from news.models import News
from contacts.models import Contact
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from collections import defaultdict


from datetime import date, timedelta
from itertools import chain, groupby
from users.models import User
from orders.models import Order
from calendar_app.models import (
    Appointment,
    Call
)


def get_user_appointments(user):
    appointments = Appointment.objects.all()

    if not (
        user.is_superuser
        or user.role in ["admin", "manager"]
    ):
        appointments = appointments.filter(agent=user)

    return appointments


def get_user_calls(user):
    calls = Call.objects.select_related(
        "contact",
        "agent",
        "news",
        "listing",
    )
    if not user_can_manage_all(user):
        calls = calls.filter(agent=user)
    return calls


def user_can_manage_all(user):
    return user.is_superuser or user.role in ["admin", "manager"]


def get_user_order_or_404(user, order_id):
    orders = Order.objects.select_related(
        "buyer",
        "buyer__assigned_agent",
        "zone",
    )
    return get_object_or_404(orders, pk=order_id)


def get_user_proposal_or_404(user, proposal_id):
    proposals = ProposalAppointment.objects.select_related(
        "order__buyer",
        "listing__property",
        "listing__owner",
        "buyer",
        "agent",
    )
    if not user_can_manage_all(user):
        proposals = proposals.filter(agent=user)
    return get_object_or_404(proposals, pk=proposal_id)


@login_required
def create_appointment(request, news_id):

    news = get_object_or_404(News, id=news_id)

    if not news.comments.exists():

        messages.warning(
            request,
            (
                "Esta noticia no tiene comentarios registrados. "
                "Se recomienda documentar la conversación antes "
                "de programar una cita."
            )
        )

    if request.method == "POST":

        form = AppointmentForm(
            request.POST or None,
            user=request.user
        )

        if form.is_valid():

            appointment = form.save(commit=False)

            appointment.news = news
            appointment.contact = news.related_property.contacts.first()
            appointment.related_property = news.related_property
            appointment.agent = request.user

            appointment.save()

            return redirect("news_detail", news.id)

    else:

        form = AppointmentForm(user=request.user)

    return render(request, "appointments/form.html", {
        "form": form,
        "news": news,
        "schedule_agent": request.user,
    })

@login_required
def create_call(request, news_id):

    news = get_object_or_404(News, id=news_id)

    if request.method == "POST":

        form = CallForm(
            request.POST or None,
            user=request.user
        )

        if form.is_valid():

            call = form.save(commit=False)

            call.news = news
            call.contact = news.related_property.contacts.first()
            call.agent = request.user

            call.save()

            return redirect("news_detail", news.id)

    else:

        form = CallForm(user=request.user)

    return render(request, "calls/form.html", {
        "form": form,
        "news": news,
        "schedule_agent": request.user,
    })


def get_user_listing_or_404(user, listing_id):
    from listings.models import Listing

    listings = Listing.objects.select_related(
        "property",
        "owner",
        "agent",
    )
    if not (
        user.is_superuser
        or user.role in ["admin", "manager"]
    ):
        listings = listings.filter(agent=user)

    return get_object_or_404(listings, pk=listing_id)


@login_required
def create_listing_appointment(request, listing_id):
    listing = get_user_listing_or_404(request.user, listing_id)

    if listing.owner is None:
        messages.error(
            request,
            "El encargo necesita un propietario antes de programar la cita.",
        )
        return redirect("listing_detail", listing_id=listing.pk)

    assigned_agent = listing.agent or request.user
    form = AppointmentForm(
        request.POST or None,
        user=assigned_agent,
        appointment_type="follow_up",
    )

    if request.method == "POST" and form.is_valid():
        appointment = form.save(commit=False)
        appointment.appointment_type = "follow_up"
        appointment.listing = listing
        appointment.contact = listing.owner
        appointment.related_property = listing.property
        appointment.agent = assigned_agent
        appointment.save()
        return redirect("listing_detail", listing_id=listing.pk)

    return render(
        request,
        "appointments/form.html",
        {
            "form": form,
            "listing": listing,
            "page_title": "Nueva cita de seguimiento",
            "schedule_agent": assigned_agent,
        },
    )


@login_required
def create_listing_call(request, listing_id):
    listing = get_user_listing_or_404(request.user, listing_id)

    if listing.owner is None:
        messages.error(
            request,
            "El encargo necesita un propietario antes de programar la llamada.",
        )
        return redirect("listing_detail", listing_id=listing.pk)

    assigned_agent = listing.agent or request.user
    form = CallForm(request.POST or None, user=assigned_agent)

    if request.method == "POST" and form.is_valid():
        call = form.save(commit=False)
        call.listing = listing
        call.contact = listing.owner
        call.agent = assigned_agent
        call.save()
        return redirect("listing_detail", listing_id=listing.pk)

    return render(
        request,
        "calls/form.html",
        {
            "form": form,
            "listing": listing,
            "page_title": "Nueva llamada de seguimiento",
            "schedule_agent": assigned_agent,
        },
    )


@login_required
def create_order_sale_appointment(request, order_id):
    order = get_user_order_or_404(request.user, order_id)
    assigned_agent = order.buyer.assigned_agent or request.user
    form = SaleAppointmentForm(
        request.POST or None,
        user=assigned_agent,
        order=order,
    )

    if request.method == "POST" and form.is_valid():
        appointment = form.save(commit=False)
        appointment.appointment_type = "sale"
        appointment.order = order
        appointment.contact = order.buyer
        appointment.related_property = appointment.listing.property
        appointment.agent = assigned_agent
        appointment.save()
        messages.success(request, "Cita de venta programada correctamente.")
        return redirect("order_detail", pk=order.pk)

    return render(
        request,
        "appointments/form.html",
        {
            "form": form,
            "order": order,
            "page_title": "Nueva cita de venta",
            "schedule_agent": assigned_agent,
        },
    )

@login_required
def appointment_detail(request, pk):

    appointment = get_object_or_404(
        get_user_appointments(request.user).select_related(
            "news",
            "related_property",
            "contact",
            "agent",
            "listing",
            "order",
            "purchase_proposal",
        ),
        pk=pk
    )

    listing = appointment.generated_listing.first()

    proposal = getattr(appointment, "proposal", None)
    if proposal is None:
        proposal = appointment.purchase_proposal
    resulting_appointments = list(
        appointment.resulting_appointments.all().order_by("date", "time")
    )

    return render(
        request,
        "calendar_app/appointment_detail.html",
        {
            "appointment": appointment,
            "result_form": AppointmentResultForm(instance=appointment),
            "listing": listing,
            "proposal": proposal,
            "proposal_appointment": getattr(
                appointment,
                "proposal_appointment",
                None,
            ),
            "counteroffer": getattr(appointment, "counteroffer", None),
            "resulting_appointments": resulting_appointments,
            "contract_appointment": next(
                (
                    item
                    for item in resulting_appointments
                    if item.appointment_type == "contract"
                ),
                None,
            ),
            "signing_appointment": next(
                (
                    item
                    for item in resulting_appointments
                    if item.appointment_type == "signing"
                ),
                None,
            ),
        }
    )


@login_required
@require_POST
def add_appointment_result(request, pk):
    appointment = get_object_or_404(
        get_user_appointments(request.user),
        pk=pk,
    )
    form = AppointmentResultForm(request.POST, instance=appointment)

    if form.is_valid():
        appointment = form.save(commit=False)
        appointment.status = "completed"
        appointment.save(update_fields=["result_comment", "status"])
        if appointment.appointment_type == "acquisition":
            success_message = (
                "Comentario guardado. Indica ahora si la cita tuvo éxito."
            )
        elif appointment.appointment_type == "sale":
            success_message = (
                "Comentario guardado. Indica si el comprador quiere hacer "
                "una propuesta."
            )
        elif appointment.appointment_type == "proposal":
            success_message = (
                "Comentario guardado. Ya puedes registrar la propuesta de compra."
            )
        elif appointment.appointment_type == "proposal_acceptance":
            success_message = (
                "Comentario guardado. Indica si la propuesta ha sido aceptada."
            )
        elif appointment.appointment_type in ["contract", "signing"]:
            success_message = "Comentario guardado y cita completada."
        else:
            success_message = "Comentario guardado y cita completada."
        messages.success(request, success_message)
    else:
        listing = appointment.generated_listing.first()
        proposal = getattr(appointment, "proposal", None)
        if proposal is None:
            proposal = appointment.purchase_proposal
        return render(
            request,
            "calendar_app/appointment_detail.html",
            {
                "appointment": appointment,
                "result_form": form,
                "listing": listing,
                "proposal": proposal,
                "proposal_appointment": getattr(
                    appointment,
                    "proposal_appointment",
                    None,
                ),
                "counteroffer": getattr(appointment, "counteroffer", None),
                "resulting_appointments": appointment.resulting_appointments.all(),
            },
            status=400,
        )

    return redirect("appointment_detail", pk=appointment.pk)


@login_required
def create_proposal_appointment(request, pk):
    sale_appointment = get_object_or_404(
        get_user_appointments(request.user).select_related(
            "order__buyer",
            "listing__property",
            "agent",
        ),
        pk=pk,
        appointment_type="sale",
    )

    if (
        sale_appointment.status != "completed"
        or not sale_appointment.result_comment.strip()
    ):
        messages.warning(
            request,
            "Añade el comentario de la cita de venta antes de programar la cita de propuesta.",
        )
        return redirect("appointment_detail", pk=sale_appointment.pk)

    if sale_appointment.order is None or sale_appointment.listing is None:
        messages.error(
            request,
            "La cita de venta no tiene un pedido y un encargo relacionados.",
        )
        return redirect("appointment_detail", pk=sale_appointment.pk)

    existing_appointment = getattr(
        sale_appointment,
        "proposal_appointment",
        None,
    )
    if existing_appointment is not None:
        return redirect("appointment_detail", pk=existing_appointment.pk)

    assigned_agent = sale_appointment.agent or request.user
    form = AppointmentForm(
        request.POST or None,
        user=assigned_agent,
        appointment_type="proposal",
    )
    if request.method == "POST" and form.is_valid():
        proposal_appointment = form.save(commit=False)
        proposal_appointment.appointment_type = "proposal"
        proposal_appointment.source_sale_appointment = sale_appointment
        proposal_appointment.order = sale_appointment.order
        proposal_appointment.listing = sale_appointment.listing
        proposal_appointment.contact = sale_appointment.contact
        proposal_appointment.related_property = sale_appointment.related_property
        proposal_appointment.agent = assigned_agent
        proposal_appointment.save()

        sale_appointment.result_success = True
        sale_appointment.save(update_fields=["result_success"])
        messages.success(request, "Cita de propuesta programada correctamente.")
        return redirect("appointment_detail", pk=proposal_appointment.pk)

    return render(
        request,
        "appointments/form.html",
        {
            "form": form,
            "order": sale_appointment.order,
            "listing": sale_appointment.listing,
            "page_title": "Nueva cita de propuesta",
            "schedule_agent": assigned_agent,
        },
    )


@login_required
def create_purchase_proposal(request, pk):
    appointment = get_object_or_404(
        get_user_appointments(request.user).select_related(
            "order__buyer",
            "listing__property",
            "agent",
        ),
        pk=pk,
        appointment_type="proposal",
    )

    if appointment.status != "completed" or not appointment.result_comment.strip():
        messages.warning(
            request,
            "Añade el comentario de la cita de propuesta antes de registrar la oferta.",
        )
        return redirect("appointment_detail", pk=appointment.pk)

    if appointment.order is None or appointment.listing is None:
        messages.error(
            request,
            "La cita de propuesta no tiene un pedido y un encargo relacionados.",
        )
        return redirect("appointment_detail", pk=appointment.pk)

    existing_proposal = getattr(appointment, "proposal", None)
    if existing_proposal is not None:
        return redirect("proposal_appointment_detail", pk=existing_proposal.pk)

    form = ProposalAppointmentForm(
        request.POST or None,
        initial={"proposal_date": date.today()},
    )
    if request.method == "POST" and form.is_valid():
        proposal = form.save(commit=False)
        proposal.source_sale_appointment = appointment
        proposal.order = appointment.order
        proposal.listing = appointment.listing
        proposal.buyer = appointment.contact
        proposal.agent = appointment.agent
        proposal.listing_price = appointment.listing.agency_price
        proposal.save()
        messages.success(request, "Propuesta de compra registrada correctamente.")
        return redirect("proposal_appointment_detail", pk=proposal.pk)

    return render(
        request,
        "calendar_app/proposal_form.html",
        {
            "form": form,
            "appointment": appointment,
            "listing_price": appointment.listing.agency_price,
        },
    )


@login_required
@require_POST
def decline_sale_proposal(request, pk):
    appointment = get_object_or_404(
        get_user_appointments(request.user),
        pk=pk,
        appointment_type="sale",
    )
    if appointment.status != "completed" or not appointment.result_comment.strip():
        messages.warning(
            request,
            "Añade el comentario antes de registrar la decisión del comprador.",
        )
        return redirect("appointment_detail", pk=appointment.pk)

    appointment.result_success = False
    appointment.save(update_fields=["result_success"])
    messages.success(request, "Se ha registrado que no realizará una propuesta.")
    return redirect("appointment_detail", pk=appointment.pk)


@login_required
def proposal_appointment_detail(request, pk):
    proposals = ProposalAppointment.objects.select_related(
        "source_sale_appointment",
        "order",
        "listing__property",
        "buyer",
        "agent",
    )
    if not user_can_manage_all(request.user):
        proposals = proposals.filter(agent=request.user)
    proposal = get_object_or_404(proposals, pk=pk)
    appointments = proposal.appointments.select_related(
        "agent",
        "contact",
    ).order_by("-date", "-time")
    return render(
        request,
        "calendar_app/proposal_detail.html",
        {
            "proposal": proposal,
            "appointments": appointments,
            "counteroffers": proposal.counteroffers.all(),
        },
    )


@login_required
def create_acceptance_appointment(request, proposal_id):
    proposal = get_user_proposal_or_404(request.user, proposal_id)
    if proposal.status in [
        "accepted",
        "contract_appointment",
        "signing_appointment",
    ]:
        messages.warning(
            request,
            "La propuesta ya fue aceptada y ha continuado a la fase final.",
        )
        return redirect("proposal_appointment_detail", pk=proposal.pk)

    existing = proposal.appointments.filter(
        appointment_type="proposal_acceptance",
        status="scheduled",
    ).first()
    if existing:
        messages.info(request, "Esta propuesta ya tiene una cita de aceptación pendiente.")
        return redirect("appointment_detail", pk=existing.pk)

    assigned_agent = proposal.agent or request.user
    form = AppointmentForm(
        request.POST or None,
        user=assigned_agent,
        appointment_type="proposal_acceptance",
    )
    if request.method == "POST" and form.is_valid():
        appointment = form.save(commit=False)
        appointment.appointment_type = "proposal_acceptance"
        appointment.purchase_proposal = proposal
        appointment.order = proposal.order
        appointment.listing = proposal.listing
        appointment.contact = proposal.listing.owner or proposal.buyer
        appointment.related_property = proposal.listing.property
        appointment.agent = assigned_agent
        appointment.save()
        messages.success(request, "Cita de aceptación programada correctamente.")
        return redirect("appointment_detail", pk=appointment.pk)

    return render(
        request,
        "appointments/form.html",
        {
            "form": form,
            "order": proposal.order,
            "listing": proposal.listing,
            "proposal": proposal,
            "page_title": "Nueva cita de aceptación de propuesta",
            "schedule_agent": assigned_agent,
        },
    )


@login_required
def create_post_acceptance_appointment(request, pk, appointment_type):
    if appointment_type not in ["contract", "signing"]:
        messages.error(request, "El tipo de cita solicitado no es válido.")
        return redirect("appointment_detail", pk=pk)

    acceptance = get_object_or_404(
        get_user_appointments(request.user).select_related(
            "purchase_proposal__buyer",
            "purchase_proposal__listing__property",
            "purchase_proposal__order",
            "agent",
        ),
        pk=pk,
        appointment_type="proposal_acceptance",
    )
    if acceptance.status != "completed" or not acceptance.result_comment.strip():
        messages.warning(
            request,
            "Añade el comentario de la cita de aceptación antes de continuar.",
        )
        return redirect("appointment_detail", pk=acceptance.pk)

    if acceptance.result_success is False or hasattr(acceptance, "counteroffer"):
        messages.warning(
            request,
            "Esta cita terminó con una contraoferta. Programa una nueva cita de aceptación desde la propuesta para continuar.",
        )
        return redirect("appointment_detail", pk=acceptance.pk)

    proposal = acceptance.purchase_proposal
    if proposal is None:
        messages.error(request, "La cita no tiene una propuesta relacionada.")
        return redirect("appointment_detail", pk=acceptance.pk)

    existing = acceptance.resulting_appointments.filter(
        appointment_type=appointment_type,
    ).first()
    if existing:
        return redirect("appointment_detail", pk=existing.pk)

    assigned_agent = acceptance.agent or request.user
    form = AppointmentForm(
        request.POST or None,
        user=assigned_agent,
        appointment_type=appointment_type,
    )
    if request.method == "POST" and form.is_valid():
        appointment = form.save(commit=False)
        appointment.appointment_type = appointment_type
        appointment.purchase_proposal = proposal
        appointment.source_acceptance_appointment = acceptance
        appointment.order = proposal.order
        appointment.listing = proposal.listing
        appointment.contact = proposal.buyer
        appointment.related_property = proposal.listing.property
        appointment.agent = assigned_agent
        appointment.save()

        if acceptance.result_success is not True:
            acceptance.result_success = True
            acceptance.save(update_fields=["result_success"])

        label = "contrato" if appointment_type == "contract" else "escrituración"
        messages.success(request, f"Cita de {label} programada correctamente.")
        return redirect("appointment_detail", pk=appointment.pk)

    label = "contrato" if appointment_type == "contract" else "escrituración"
    return render(
        request,
        "appointments/form.html",
        {
            "form": form,
            "order": proposal.order,
            "listing": proposal.listing,
            "proposal": proposal,
            "page_title": f"Nueva cita de {label}",
            "schedule_agent": assigned_agent,
        },
    )


@login_required
def create_counteroffer(request, pk):
    acceptance = get_object_or_404(
        get_user_appointments(request.user).select_related(
            "purchase_proposal__listing",
            "purchase_proposal__order",
        ),
        pk=pk,
        appointment_type="proposal_acceptance",
    )
    if acceptance.status != "completed" or not acceptance.result_comment.strip():
        messages.warning(
            request,
            "Añade el comentario de la cita de aceptación antes de continuar.",
        )
        return redirect("appointment_detail", pk=acceptance.pk)

    if acceptance.result_success is True or acceptance.resulting_appointments.exists():
        messages.warning(
            request,
            "La propuesta ya fue aceptada y tiene citas finales relacionadas.",
        )
        return redirect("appointment_detail", pk=acceptance.pk)

    proposal = acceptance.purchase_proposal
    if proposal is None:
        messages.error(request, "La cita no tiene una propuesta relacionada.")
        return redirect("appointment_detail", pk=acceptance.pk)

    existing = getattr(acceptance, "counteroffer", None)
    if existing:
        return redirect("counteroffer_detail", pk=existing.pk)

    form = CounterOfferForm(
        request.POST or None,
        initial={"counteroffer_date": date.today()},
    )
    if request.method == "POST" and form.is_valid():
        counteroffer = form.save(commit=False)
        counteroffer.proposal = proposal
        counteroffer.source_acceptance_appointment = acceptance
        counteroffer.save()

        acceptance.result_success = False
        acceptance.save(update_fields=["result_success"])
        messages.success(request, "Contraoferta registrada correctamente.")
        return redirect("counteroffer_detail", pk=counteroffer.pk)

    return render(
        request,
        "calendar_app/counteroffer_form.html",
        {
            "form": form,
            "appointment": acceptance,
            "proposal": proposal,
        },
    )


@login_required
def counteroffer_detail(request, pk):
    counteroffers = CounterOffer.objects.select_related(
        "proposal__listing__property",
        "proposal__order",
        "proposal__buyer",
        "source_acceptance_appointment",
    )
    if not user_can_manage_all(request.user):
        counteroffers = counteroffers.filter(proposal__agent=request.user)
    counteroffer = get_object_or_404(counteroffers, pk=pk)
    return render(
        request,
        "calendar_app/counteroffer_detail.html",
        {"counteroffer": counteroffer},
    )


@login_required
@require_POST
def schedule_call_from_appointment(request, pk):
    appointment = get_object_or_404(
        get_user_appointments(request.user),
        pk=pk,
    )

    if (
        appointment.status != "completed"
        or not appointment.result_comment.strip()
    ):
        messages.warning(
            request,
            "Añade el comentario de resultado antes de programar la llamada.",
        )
        return redirect("appointment_detail", pk=appointment.pk)

    if appointment.news is None:
        messages.error(request, "La cita no tiene una noticia asociada.")
        return redirect("appointment_detail", pk=appointment.pk)

    appointment.result_success = False
    appointment.save(update_fields=["result_success"])

    return redirect("create_call", news_id=appointment.news_id)

@login_required
def call_detail(request, pk):

    call = get_object_or_404(
        get_user_calls(request.user),
        pk=pk,
    )

    return render(
        request,
        "calendar_app/call_detail.html",
        {
            "call": call,
            "comments": call.comments.select_related("user"),
            "comment_form": CallCommentForm(),
        }
    )


@login_required
@require_POST
def add_call_comment(request, pk):
    call = get_object_or_404(get_user_calls(request.user), pk=pk)
    form = CallCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.call = call
        comment.user = request.user
        comment.save()
        messages.success(request, "Comentario añadido a la llamada.")
        return redirect("call_detail", pk=call.pk)

    return render(
        request,
        "calendar_app/call_detail.html",
        {
            "call": call,
            "comments": call.comments.select_related("user"),
            "comment_form": form,
        },
        status=400,
    )

@login_required
def update_appointment_status(request, appointment_id, status):

    appointment = get_object_or_404(
        get_user_appointments(request.user),
        id=appointment_id,
    )

    if (
        status == "completed"
        and appointment.appointment_type in [
            "acquisition",
            "follow_up",
            "sale",
            "proposal",
            "proposal_acceptance",
            "contract",
            "signing",
        ]
        and not appointment.result_comment.strip()
    ):
        messages.warning(
            request,
            "Añade un comentario para marcar la cita como completada.",
        )
    elif status in ["completed", "cancelled", "scheduled"]:

        appointment.status = status
        appointment.save()

    return redirect(
        "appointment_detail",
        appointment.id
    )

@login_required
@require_POST
def update_call_status(request, call_id, status):

    call = get_object_or_404(
        get_user_calls(request.user),
        id=call_id,
    )

    if status in ["completed", "cancelled", "pending"]:

        call.status = status
        call.save()
        messages.success(
            request,
            f"La llamada se ha marcado como {call.get_status_display().lower()}.",
        )

    return redirect(
        "call_detail",
        call.id
    )

@login_required
def calendar_view(request):

    today = date.today()
    tomorrow = today + timedelta(days=1)
    selected_agent_ids = request.GET.getlist("agents")
    calls = Call.objects.all()
    appointments = Appointment.objects.all()
    calls = calls.exclude(status="cancelled")
    appointments = appointments.exclude(status="cancelled")

    if user_can_manage_all(request.user):
        if selected_agent_ids:
            calls = calls.filter(agent_id__in=selected_agent_ids)
            appointments = appointments.filter(agent_id__in=selected_agent_ids)
    else:
        selected_agent_ids = [str(request.user.pk)]
        calls = calls.filter(agent=request.user)
        appointments = appointments.filter(agent=request.user)

    today_calls = calls.filter(date=today)

    for item in today_calls:
        item.event_type = "call"

    today_appointments = appointments.filter(date=today)

    for item in today_appointments:
        item.event_type = "appointment"

    today_events = sorted(
        chain(
            today_calls,
            today_appointments
        ),
        key=lambda x: x.time
    )

    tomorrow_calls = calls.filter(date=tomorrow)

    for item in tomorrow_calls:
        item.event_type = "call"

    tomorrow_appointments = appointments.filter(date=tomorrow)

    for item in tomorrow_appointments:
        item.event_type = "appointment"

    tomorrow_events = sorted(
        chain(
            tomorrow_calls,
            tomorrow_appointments
        ),
        key=lambda x: x.time
    )
    agents = User.objects.filter(
        role="agent"
    )

    
    events = []

    for call in calls:
        if not call.date:
            continue

        events.append({
            "type": "call",
            "date": call.date,
            "time": call.time,
            "object": call
        })

    for appt in appointments:
        if not appt.date:
            continue

        events.append({
            "type": "appointment",
            "date": appt.date,
            "time": appt.time,
            "object": appt
        })

    # 🔥 ORDEN ÚNICO (IMPORTANTE)
    events = sorted(events, key=lambda e: (e["date"], e["time"]))

    # 🔥 GROUPBY CORRECTO
    agenda_by_day = [
        (day, list(group))
        for day, group in groupby(events, key=lambda e: e["date"])
    ]

    
    return render(
        request,
        "calendar_app/calendar.html",
        {
            "today_events": today_events,
            "tomorrow_events": tomorrow_events,
            "agents" : agents,
            "agenda_by_day" : agenda_by_day,
            "selected_agent_ids": selected_agent_ids,
        }
    )

@login_required
def calendar_events(request):

    agent_ids = request.GET.getlist("agents")

    # BASE QUERYSET
    appointments = Appointment.objects.exclude(status="cancelled")
    calls = Call.objects.exclude(status="cancelled")

    # SI NO ES MANAGER → solo sus eventos
    if not user_can_manage_all(request.user):

        appointments = appointments.filter(agent=request.user)
        calls = calls.filter(agent=request.user)

    # SI ES MANAGER Y HAY FILTRO DE AGENTES
    elif agent_ids:

        appointments = appointments.filter(agent_id__in=agent_ids)
        calls = calls.filter(agent_id__in=agent_ids)


    events = []
    
    for appointment in appointments:

        events.append({
            "id": f"appointment-{appointment.id}",
            "title": (
                f"📅 Cita de {appointment.get_appointment_type_display()}\n"
                f"{appointment.related_property.full_address}"
            ),
            "start": (
                f"{appointment.date}"
                f"T"
                f"{appointment.time}"
            ),
            "color": "#16a34a",
            "url": reverse(
                "appointment_detail",
                args=[appointment.id]
            )
        })


    for call in calls:

        events.append({
            "id": f"call-{call.id}",
            "title": (
                f"📞 Llamada a "
                f"{call.contact.name}"
            ),
            "start": (
                f"{call.date}"
                f"T"
                f"{call.time}"
            ),
            "color": "#2563eb",
            "url": reverse(
                "call_detail",
                args=[call.id]
            )
        })

    return JsonResponse(
        events,
        safe=False
    )

@login_required
def agenda(request):

    appointments = Appointment.objects.filter(
        agent=request.user
    ).exclude(status="cancelled")

    calls = Call.objects.filter(
        agent=request.user
    ).exclude(status="cancelled")

    events = []

    for appointment in appointments:

        events.append({
            "type": "appointment",
            "date": appointment.date,
            "time": appointment.time,
            "object": appointment,
        })

    for call in calls:

        events.append({
            "type": "call",
            "date": call.date,
            "time": call.time,
            "object": call,
        })

    events.sort(
        key=lambda x: (
            x["date"],
            x["time"]
        )
    )

    return render(
        request,
        "calendar_app/agenda.html",
        {
            "events": events
        }
    )


@login_required
@never_cache
def available_slots(request):

    selected_date = request.GET.get("date")
    selected_agent = request.user
    requested_agent_id = request.GET.get("agent_id")

    if requested_agent_id and user_can_manage_all(request.user):
        selected_agent = get_object_or_404(User, pk=requested_agent_id)

    appointments = Appointment.objects.filter(
        agent=selected_agent,
        date=selected_date,
        status="scheduled"
    ).values_list(
        "time",
        flat=True
    )

    calls = Call.objects.filter(
        agent=selected_agent,
        date=selected_date,
        status="pending"
    ).values_list(
        "time",
        flat=True
    )

    occupied = [
        t.strftime("%H:%M")
        for t in chain(
            appointments,
            calls
        )
    ]

    return JsonResponse({
        "occupied": occupied
    })
