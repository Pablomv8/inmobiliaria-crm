from django.db import migrations


def sync_existing_workflows(apps, schema_editor):
    Appointment = apps.get_model("calendar_app", "Appointment")
    Call = apps.get_model("calendar_app", "Call")
    Proposal = apps.get_model("calendar_app", "ProposalAppointment")
    Listing = apps.get_model("listings", "Listing")
    News = apps.get_model("news", "News")
    NewsComment = apps.get_model("news", "NewsComment")
    Order = apps.get_model("orders", "Order")

    for news in News.objects.exclude(status="closed").iterator():
        if Listing.objects.filter(source_appointment__news_id=news.pk).exists():
            status = "closed"
        elif Appointment.objects.filter(
            news_id=news.pk,
            status="scheduled",
        ).exists():
            status = "appointment"
        elif Call.objects.filter(news_id=news.pk, status="pending").exists():
            status = "follow_up"
        elif (
            NewsComment.objects.filter(news_id=news.pk).exists()
            or Appointment.objects.filter(news_id=news.pk).exists()
            or Call.objects.filter(news_id=news.pk).exists()
        ):
            status = "contacted"
        else:
            status = "new"
        News.objects.filter(pk=news.pk).update(status=status)

    for listing in Listing.objects.iterator():
        if listing.status in ["cancelled", "sold", "rented"]:
            status = "closed"
        elif Proposal.objects.filter(listing_id=listing.pk).exists():
            status = "proposal"
        elif Appointment.objects.filter(
            listing_id=listing.pk,
            appointment_type="proposal",
            status="scheduled",
        ).exists():
            status = "proposal_appointment"
        elif Appointment.objects.filter(
            listing_id=listing.pk,
            appointment_type="sale",
            status="scheduled",
        ).exists():
            status = "sale_appointment"
        elif Appointment.objects.filter(
            listing_id=listing.pk,
            appointment_type="follow_up",
            status="scheduled",
        ).exists():
            status = "follow_up_appointment"
        else:
            status = "active"
        Listing.objects.filter(pk=listing.pk).update(workflow_status=status)

    for order in Order.objects.exclude(status__in=["closed", "cancelled"]).iterator():
        if Proposal.objects.filter(order_id=order.pk).exists():
            status = "proposal"
        elif Appointment.objects.filter(
            order_id=order.pk,
            appointment_type="proposal",
            status="scheduled",
        ).exists():
            status = "proposal_appointment"
        elif Appointment.objects.filter(
            order_id=order.pk,
            appointment_type="sale",
            status="scheduled",
        ).exists():
            status = "sale_appointment"
        else:
            status = "active"
        Order.objects.filter(pk=order.pk).update(status=status)


class Migration(migrations.Migration):
    dependencies = [
        ("calendar_app", "0006_alter_proposalappointment_options_and_more"),
        ("listings", "0005_listing_workflow_status"),
        ("orders", "0003_order_status"),
    ]

    operations = [
        migrations.RunPython(sync_existing_workflows, migrations.RunPython.noop),
    ]
