from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from activities.utils import log_activity
from calendar_app.models import CallComment, ProposalComment
from listings.models import ListingComment
from news.models import NewsComment
from orders.models import OrderComment
from properties.models import PropertyComment
from users.permissions import can_manage_office


COMMENT_TYPES = {
    "property": (PropertyComment, "property", "property_detail"),
    "news": (NewsComment, "news", "news_detail"),
    "order": (OrderComment, "order", "order_detail"),
    "listing": (ListingComment, "listing", "listing_detail"),
    "call": (CallComment, "call", "call_detail"),
    "proposal": (
        ProposalComment,
        "proposal",
        "proposal_appointment_detail",
    ),
}


def _comment_or_404(kind, pk):
    definition = COMMENT_TYPES.get(kind)
    if definition is None:
        raise PermissionDenied
    model, parent_field, detail_url = definition
    comment = get_object_or_404(model.objects.select_related("user"), pk=pk)
    return comment, parent_field, detail_url


def _return_to_parent(comment, parent_field, detail_url):
    parent = getattr(comment, parent_field)
    if detail_url == "listing_detail":
        return redirect(detail_url, listing_id=parent.pk)
    return redirect(detail_url, pk=parent.pk)


@login_required
def comment_edit(request, kind, pk):
    comment, parent_field, detail_url = _comment_or_404(kind, pk)
    if not comment.can_be_edited_by(request.user):
        raise PermissionDenied

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if not text:
            messages.error(request, "El comentario no puede quedar vacío.")
        else:
            if not comment.original_text:
                comment.original_text = comment.text
            comment.text = text
            comment.edited_at = timezone.now()
            comment.save(update_fields=["text", "original_text", "edited_at"])
            log_activity(
                request.user,
                "comment_edited",
                f"Corrigió el comentario {kind} #{comment.pk}; se conserva el texto original.",
            )
            messages.success(request, "Comentario corregido. El cambio ha quedado auditado.")
            return _return_to_parent(comment, parent_field, detail_url)

    return render(
        request,
        "comments/edit.html",
        {"comment": comment, "kind": kind},
    )


@login_required
@require_POST
def comment_hide(request, kind, pk):
    if not can_manage_office(request.user):
        raise PermissionDenied
    comment, parent_field, detail_url = _comment_or_404(kind, pk)
    if not comment.is_hidden:
        comment.is_hidden = True
        comment.hidden_at = timezone.now()
        comment.hidden_by = request.user
        comment.save(update_fields=["is_hidden", "hidden_at", "hidden_by"])
        log_activity(
            request.user,
            "comment_hidden",
            f"Ocultó el comentario {kind} #{comment.pk} sin eliminarlo.",
        )
        messages.success(request, "El comentario se ha ocultado y permanece en el historial.")
    return _return_to_parent(comment, parent_field, detail_url)
