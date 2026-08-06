from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from listings.models import Listing
from news.models import NewsComment

from .models import Appointment, Call, CounterOffer, ProposalAppointment
from .workflow import (
    sync_listing_workflow_status,
    sync_news_status,
    sync_order_status,
    sync_proposal_status,
)


def _appointment_relations(instance):
    return {
        "news_ids": {instance.news_id} if instance.news_id else set(),
        "listing_ids": {instance.listing_id} if instance.listing_id else set(),
        "order_ids": {instance.order_id} if instance.order_id else set(),
        "proposal_ids": (
            {instance.purchase_proposal_id}
            if instance.purchase_proposal_id
            else set()
        ),
    }


@receiver(pre_save, sender=Appointment)
def remember_previous_appointment_relations(sender, instance, **kwargs):
    instance._previous_workflow_relations = {
        "news_ids": set(),
        "listing_ids": set(),
        "order_ids": set(),
        "proposal_ids": set(),
    }
    if not instance.pk:
        return

    previous = sender.objects.filter(pk=instance.pk).only(
        "news_id",
        "listing_id",
        "order_id",
        "purchase_proposal_id",
    ).first()
    if previous:
        instance._previous_workflow_relations = _appointment_relations(previous)


@receiver(post_save, sender=Appointment)
def sync_appointment_relations(sender, instance, **kwargs):
    relations = _appointment_relations(instance)
    previous = getattr(instance, "_previous_workflow_relations", {})
    for news_id in relations["news_ids"] | previous.get("news_ids", set()):
        sync_news_status(news_id)
    for listing_id in relations["listing_ids"] | previous.get("listing_ids", set()):
        sync_listing_workflow_status(listing_id)
    for order_id in relations["order_ids"] | previous.get("order_ids", set()):
        sync_order_status(order_id)
    for proposal_id in relations["proposal_ids"] | previous.get("proposal_ids", set()):
        sync_proposal_status(proposal_id)


@receiver(pre_delete, sender=Appointment)
def remember_deleted_appointment_relations(sender, instance, **kwargs):
    instance._deleted_workflow_relations = _appointment_relations(instance)


@receiver(post_delete, sender=Appointment)
def sync_deleted_appointment_relations(sender, instance, **kwargs):
    relations = getattr(instance, "_deleted_workflow_relations", {})
    for news_id in relations.get("news_ids", set()):
        sync_news_status(news_id)
    for listing_id in relations.get("listing_ids", set()):
        sync_listing_workflow_status(listing_id)
    for order_id in relations.get("order_ids", set()):
        sync_order_status(order_id)
    for proposal_id in relations.get("proposal_ids", set()):
        sync_proposal_status(proposal_id)


@receiver(post_save, sender=Call)
@receiver(post_delete, sender=Call)
def sync_call_news(sender, instance, **kwargs):
    sync_news_status(instance.news_id)


@receiver(post_save, sender=NewsComment)
@receiver(post_delete, sender=NewsComment)
def sync_comment_news(sender, instance, **kwargs):
    sync_news_status(instance.news_id)


@receiver(post_save, sender=Listing)
def sync_listing_and_source_news(sender, instance, **kwargs):
    sync_listing_workflow_status(instance.pk)
    if instance.source_appointment_id:
        news_id = Appointment.objects.filter(
            pk=instance.source_appointment_id,
        ).values_list("news_id", flat=True).first()
        sync_news_status(news_id)


@receiver(post_save, sender=ProposalAppointment)
@receiver(post_delete, sender=ProposalAppointment)
def sync_proposal_relations(sender, instance, **kwargs):
    sync_listing_workflow_status(instance.listing_id)
    sync_order_status(instance.order_id)
    sync_proposal_status(instance.pk)


@receiver(post_save, sender=CounterOffer)
def sync_counteroffer_relations(sender, instance, **kwargs):
    sync_proposal_status(instance.proposal_id)
    sync_listing_workflow_status(instance.proposal.listing_id)
    sync_order_status(instance.proposal.order_id)


@receiver(pre_delete, sender=CounterOffer)
def remember_deleted_counteroffer_relations(sender, instance, **kwargs):
    instance._deleted_counteroffer_relations = (
        instance.proposal_id,
        instance.proposal.listing_id,
        instance.proposal.order_id,
    )


@receiver(post_delete, sender=CounterOffer)
def sync_deleted_counteroffer_relations(sender, instance, **kwargs):
    proposal_id, listing_id, order_id = getattr(
        instance,
        "_deleted_counteroffer_relations",
        (None, None, None),
    )
    sync_proposal_status(proposal_id)
    sync_listing_workflow_status(listing_id)
    sync_order_status(order_id)
