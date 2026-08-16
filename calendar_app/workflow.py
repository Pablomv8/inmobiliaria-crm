from calendar_app.models import (
    Appointment,
    Call,
    CounterOffer,
    ProposalAppointment,
)
from listings.models import Listing
from news.models import News
from orders.models import Order


def _latest_negotiation_status(*, listing_id=None, order_id=None):
    appointment_filters = {
        "appointment_type": "proposal",
        "status": "scheduled",
    }
    proposal_filters = {}
    counteroffer_filters = {}

    if listing_id is not None:
        appointment_filters["listing_id"] = listing_id
        proposal_filters["listing_id"] = listing_id
        counteroffer_filters["proposal__listing_id"] = listing_id
    elif order_id is not None:
        appointment_filters["order_id"] = order_id
        proposal_filters["order_id"] = order_id
        counteroffer_filters["proposal__order_id"] = order_id
    else:
        return None

    stages = []
    proposal_appointment_date = Appointment.objects.filter(
        **appointment_filters,
    ).order_by("-created_at").values_list("created_at", flat=True).first()
    proposal_date = ProposalAppointment.objects.filter(
        **proposal_filters,
    ).order_by("-created_at").values_list("created_at", flat=True).first()
    counteroffer_date = CounterOffer.objects.filter(
        **counteroffer_filters,
    ).order_by("-created_at").values_list("created_at", flat=True).first()

    if proposal_appointment_date:
        stages.append((proposal_appointment_date, "proposal_appointment"))
    if proposal_date:
        stages.append((proposal_date, "proposal"))
    if counteroffer_date:
        stages.append((counteroffer_date, "counteroffer"))

    return max(stages, default=(None, None), key=lambda item: item[0])[1]


def sync_news_status(news_id):
    if not news_id:
        return

    news = News.objects.filter(pk=news_id).first()
    if news is None or news.status == "closed":
        return

    if Listing.objects.filter(source_appointment__news_id=news_id).exists():
        status = "closed"
    elif Appointment.objects.filter(
        news_id=news_id,
        status="scheduled",
    ).exists():
        status = "appointment"
    elif Call.objects.filter(news_id=news_id, status="pending").exists():
        status = "follow_up"
    elif (
        news.comments.exists()
        or Appointment.objects.filter(news_id=news_id).exists()
        or Call.objects.filter(news_id=news_id).exists()
    ):
        status = "contacted"
    else:
        status = "new"

    News.objects.filter(pk=news_id).exclude(status=status).update(status=status)


def sync_listing_workflow_status(listing_id):
    if not listing_id:
        return

    listing = Listing.objects.filter(pk=listing_id).only("status").first()
    if listing is None:
        return

    negotiation_status = _latest_negotiation_status(listing_id=listing_id)

    if listing.status in ["cancelled", "sold", "rented"]:
        workflow_status = "closed"
    elif Appointment.objects.filter(
        listing_id=listing_id,
        appointment_type="signing",
        status="scheduled",
    ).exists():
        workflow_status = "signing_appointment"
    elif Appointment.objects.filter(
        listing_id=listing_id,
        appointment_type="contract",
        status="scheduled",
    ).exists():
        workflow_status = "contract_appointment"
    elif Appointment.objects.filter(
        listing_id=listing_id,
        appointment_type="proposal_acceptance",
        status="scheduled",
    ).exists():
        workflow_status = "acceptance_appointment"
    elif negotiation_status:
        workflow_status = negotiation_status
    elif Appointment.objects.filter(
        listing_id=listing_id,
        appointment_type="sale",
        status="scheduled",
    ).exists():
        workflow_status = "sale_appointment"
    elif Appointment.objects.filter(
        listing_id=listing_id,
        appointment_type="follow_up",
        status="scheduled",
    ).exists():
        workflow_status = "follow_up_appointment"
    else:
        workflow_status = "active"

    Listing.objects.filter(pk=listing_id).exclude(
        workflow_status=workflow_status,
    ).update(workflow_status=workflow_status)


def sync_order_status(order_id):
    if not order_id:
        return

    order = Order.objects.filter(pk=order_id).only("status").first()
    if order is None or order.status in ["closed", "cancelled"]:
        return

    negotiation_status = _latest_negotiation_status(order_id=order_id)

    if Appointment.objects.filter(
        order_id=order_id,
        appointment_type="signing",
        status="scheduled",
    ).exists():
        status = "signing_appointment"
    elif Appointment.objects.filter(
        order_id=order_id,
        appointment_type="contract",
        status="scheduled",
    ).exists():
        status = "contract_appointment"
    elif Appointment.objects.filter(
        order_id=order_id,
        appointment_type="proposal_acceptance",
        status="scheduled",
    ).exists():
        status = "acceptance_appointment"
    elif negotiation_status:
        status = negotiation_status
    elif Appointment.objects.filter(
        order_id=order_id,
        appointment_type="sale",
        status="scheduled",
    ).exists():
        status = "sale_appointment"
    else:
        status = "active"

    Order.objects.filter(pk=order_id).exclude(status=status).update(status=status)


def sync_proposal_status(proposal_id):
    if not proposal_id:
        return

    proposal = ProposalAppointment.objects.filter(pk=proposal_id).first()
    if proposal is None:
        return

    appointments = Appointment.objects.filter(purchase_proposal_id=proposal_id)
    if appointments.filter(
        appointment_type="signing",
        status="scheduled",
    ).exists():
        status = "signing_appointment"
    elif appointments.filter(
        appointment_type="contract",
        status="scheduled",
    ).exists():
        status = "contract_appointment"
    elif appointments.filter(
        appointment_type="proposal_acceptance",
        status="scheduled",
    ).exists():
        status = "acceptance_appointment"
    elif CounterOffer.objects.filter(proposal_id=proposal_id).exists():
        status = "counteroffer"
    elif appointments.filter(
        appointment_type="proposal_acceptance",
        status="completed",
        result_success=True,
    ).exists():
        status = "accepted"
    else:
        status = "submitted"

    ProposalAppointment.objects.filter(pk=proposal_id).exclude(
        status=status,
    ).update(status=status)
