from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from listings.models import Listing
from news.models import NewsComment

from .models import Appointment, Call, ProposalAppointment
from .workflow import (
    sync_listing_workflow_status,
    sync_news_status,
    sync_order_status,
)


def _appointment_relations(instance):
    return {
        "news_ids": {instance.news_id} if instance.news_id else set(),
        "listing_ids": {instance.listing_id} if instance.listing_id else set(),
        "order_ids": {instance.order_id} if instance.order_id else set(),
    }


@receiver(pre_save, sender=Appointment)
def remember_previous_appointment_relations(sender, instance, **kwargs):
    instance._previous_workflow_relations = {
        "news_ids": set(),
        "listing_ids": set(),
        "order_ids": set(),
    }
    if not instance.pk:
        return

    previous = sender.objects.filter(pk=instance.pk).only(
        "news_id",
        "listing_id",
        "order_id",
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
