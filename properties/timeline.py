from datetime import datetime, time

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from calendar_app.models import Appointment, Call, CounterOffer, ProposalAppointment


def aware_datetime(day, value=time.min):
    result = datetime.combine(day, value)
    return timezone.make_aware(result, timezone.get_current_timezone())


def user_name(user):
    if user is None:
        return "Usuario eliminado"
    return user.get_full_name() or user.username


def can_open_agent_event(viewer, agent):
    return (
        viewer.is_superuser
        or viewer.role in ["admin", "manager"]
        or viewer == agent
    )


def build_property_timeline(property_obj, viewer):
    events = [{
        "timestamp": property_obj.created_at,
        "type": "creation",
        "icon": "🏠",
        "title": "Inmueble creado",
        "description": property_obj.full_address,
        "url": "",
    }]

    for history in property_obj.status_history.all():
        events.append({
            "timestamp": history.created_at,
            "type": "status",
            "icon": "🔄",
            "title": "Cambio de estado",
            "description": (
                f"{history.get_old_status_display()} → "
                f"{history.get_new_status_display()}"
            ),
            "url": "",
        })

    for comment in property_obj.comments.select_related("user"):
        events.append({
            "timestamp": comment.created_at,
            "type": "comment",
            "icon": "💬",
            "title": "Contacto registrado",
            "description": f"{comment.text} · {user_name(comment.user)}",
            "url": "",
        })

    for news in property_obj.news.select_related("agent"):
        news_url = reverse("news_detail", args=[news.pk])
        events.append({
            "timestamp": news.created_at,
            "type": "news",
            "icon": "📰",
            "title": "Noticia creada",
            "description": (
                f"{news.get_motivation_display()} · "
                f"{news.get_status_display()} · {user_name(news.agent)}"
            ),
            "url": news_url,
        })
        for comment in news.comments.select_related("user"):
            events.append({
                "timestamp": comment.created_at,
                "type": "comment",
                "icon": "💬",
                "title": "Comentario en la noticia",
                "description": f"{comment.text} · {user_name(comment.user)}",
                "url": news_url,
            })

    for listing in property_obj.listings.select_related("owner", "agent"):
        listing_url = reverse("listing_detail", args=[listing.pk])
        events.append({
            "timestamp": listing.created_at,
            "type": "listing",
            "icon": "📋",
            "title": "Encargo creado",
            "description": (
                f"{listing.get_listing_type_display()} · "
                f"{listing.get_status_display()} · {user_name(listing.agent)}"
            ),
            "url": listing_url,
        })
        for comment in listing.comments.select_related("user"):
            events.append({
                "timestamp": comment.created_at,
                "type": "comment",
                "icon": "💬",
                "title": "Comentario en el encargo",
                "description": f"{comment.text} · {user_name(comment.user)}",
                "url": listing_url,
            })

    appointments = Appointment.objects.filter(
        related_property=property_obj,
    ).select_related("agent", "contact")
    for appointment in appointments:
        events.append({
            "timestamp": aware_datetime(appointment.date, appointment.time),
            "type": "appointment",
            "icon": "📅",
            "title": f"Cita de {appointment.get_appointment_type_display()}",
            "description": (
                f"{appointment.time.strftime('%H:%M')}–"
                f"{appointment.end_time.strftime('%H:%M')} · "
                f"{appointment.get_status_display()} · "
                f"{user_name(appointment.agent)}"
            ),
            "url": (
                reverse("appointment_detail", args=[appointment.pk])
                if can_open_agent_event(viewer, appointment.agent)
                else ""
            ),
        })

    calls = Call.objects.filter(
        Q(news__related_property=property_obj)
        | Q(listing__property=property_obj)
    ).select_related("agent", "contact").distinct()
    for call in calls:
        call_url = (
            reverse("call_detail", args=[call.pk])
            if can_open_agent_event(viewer, call.agent)
            else ""
        )
        events.append({
            "timestamp": aware_datetime(call.date, call.time),
            "type": "call",
            "icon": "📞",
            "title": "Llamada",
            "description": (
                f"{call.time.strftime('%H:%M')} · "
                f"{call.get_status_display()} · {user_name(call.agent)}"
            ),
            "url": call_url,
        })
        for comment in call.comments.select_related("user"):
            events.append({
                "timestamp": comment.created_at,
                "type": "comment",
                "icon": "💬",
                "title": "Comentario en la llamada",
                "description": f"{comment.text} · {user_name(comment.user)}",
                "url": call_url,
            })

    proposals = ProposalAppointment.objects.filter(
        listing__property=property_obj,
    ).select_related("buyer", "agent")
    for proposal in proposals:
        events.append({
            "timestamp": aware_datetime(proposal.proposal_date),
            "type": "proposal",
            "icon": "💶",
            "title": "Propuesta de compra",
            "description": (
                f"{proposal.offered_price} € · "
                f"{proposal.get_status_display()} · {proposal.buyer}"
            ),
            "url": (
                reverse("proposal_appointment_detail", args=[proposal.pk])
                if can_open_agent_event(viewer, proposal.agent)
                else ""
            ),
        })

    counteroffers = CounterOffer.objects.filter(
        proposal__listing__property=property_obj,
    ).select_related("proposal__agent")
    for counteroffer in counteroffers:
        events.append({
            "timestamp": aware_datetime(counteroffer.counteroffer_date),
            "type": "counteroffer",
            "icon": "↔️",
            "title": "Contraoferta",
            "description": f"El propietario solicita {counteroffer.owner_price} €",
            "url": (
                reverse("counteroffer_detail", args=[counteroffer.pk])
                if can_open_agent_event(viewer, counteroffer.proposal.agent)
                else ""
            ),
        })

    for sale in property_obj.sales.select_related("buyer", "agent"):
        events.append({
            "timestamp": aware_datetime(sale.sale_date),
            "type": "sale",
            "icon": "🤝",
            "title": "Venta registrada",
            "description": (
                f"{sale.sale_price} € · {sale.get_status_display()} · "
                f"{sale.buyer}"
            ),
            "url": reverse("sale_list"),
        })

    return sorted(
        events,
        key=lambda event: event["timestamp"],
        reverse=True,
    )
