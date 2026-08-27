from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from contacts.models import Contact
from properties.models import Property, Zone
from users.models import User

from .forms import OrderCommentForm, OrderForm
from .models import Order
from config.pagination import paginate
from users.permissions import can_manage_office, has_related_records, scope_to_user
from django.contrib import messages


@login_required
def order_list(request):
    orders = Order.objects.select_related(
        "buyer",
        "agent",
        "zone",
    )
    search = request.GET.get("search", "").strip()
    payment_type = request.GET.get("payment_type", "")
    operation_type = request.GET.get("operation_type", "")
    property_type = request.GET.get("property_type", "")
    zone = request.GET.get("zone", "")
    agent = request.GET.get("agent", "")
    status = request.GET.get("status", "")
    ordering = request.GET.get("ordering", "recent")

    if request.user.is_superuser or request.user.role in ["admin", "manager"]:
        if agent:
            orders = orders.filter(agent_id=agent)
    else:
        orders = orders.filter(agent=request.user)

    if search:
        orders = orders.filter(
            Q(buyer__name__icontains=search)
            | Q(buyer__last_name__icontains=search)
            | Q(buyer__phone__icontains=search)
        )
    if payment_type:
        orders = orders.filter(payment_type=payment_type)
    if operation_type:
        orders = orders.filter(operation_type=operation_type)
    if property_type:
        orders = orders.filter(property_type=property_type)
    if zone:
        orders = orders.filter(zone_id=zone)
    if status:
        orders = orders.filter(status=status)

    ordering_options = {
        "recent": "-created_at",
        "oldest": "created_at",
        "budget_desc": "-max_price",
        "budget_asc": "max_price",
        "buyer": "buyer__name",
    }
    orders = paginate(
        request,
        orders.order_by(ordering_options.get(ordering, "-created_at")),
    )

    return render(
        request,
        "orders/list.html",
        {
            "orders": orders,
            "page_obj": orders,
            "payment_choices": Order.PAYMENT_TYPE_CHOICES,
            "operation_choices": Order.OPERATION_TYPE_CHOICES,
            "status_choices": Order.STATUS_CHOICES,
            "property_type_choices": Property.PROPERTY_TYPE_CHOICES,
            "zones": Zone.objects.all(),
            "agents": User.objects.filter(is_active=True).order_by("username"),
        },
    )


@login_required
def order_create(request, buyer_id=None):
    buyer = None
    if buyer_id is not None:
        buyer = get_object_or_404(
            Contact,
            pk=buyer_id,
            is_buyer=True,
        )

    form = OrderForm(request.POST or None, buyer_obj=buyer, user=request.user)
    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)
        if buyer is not None:
            order.buyer = buyer
        if "agent" not in form.fields:
            order.agent = request.user
        order.save()
        return redirect("order_detail", pk=order.pk)

    return render(
        request,
        "orders/form.html",
        {
            "form": form,
            "buyer": buyer,
            "page_title": "Nuevo pedido",
            "submit_label": "Guardar pedido",
        },
    )


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        scope_to_user(
            Order.objects.select_related(
                "buyer",
                "agent",
                "zone",
            ),
            request.user,
        ),
        pk=pk,
    )
    sale_appointments = order.sale_appointments.select_related(
        "listing__property",
        "agent",
    ).order_by("-date", "-time")
    comments = order.comments.select_related("user")
    return render(
        request,
        "orders/detail.html",
        {
            "order": order,
            "sale_appointments": sale_appointments,
            "comments": comments,
            "comment_form": OrderCommentForm(),
        },
    )


@login_required
@require_POST
def order_add_comment(request, pk):
    order = get_object_or_404(
        scope_to_user(
            Order.objects.select_related(
                "buyer",
                "agent",
                "zone",
            ),
            request.user,
        ),
        pk=pk,
    )
    form = OrderCommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.order = order
        comment.user = request.user
        comment.save()
        return redirect("order_detail", pk=order.pk)

    sale_appointments = order.sale_appointments.select_related(
        "listing__property",
        "agent",
    ).order_by("-date", "-time")
    return render(
        request,
        "orders/detail.html",
        {
            "order": order,
            "sale_appointments": sale_appointments,
            "comments": order.comments.select_related("user"),
            "comment_form": form,
        },
        status=400,
    )


@login_required
def order_update(request, pk):
    order = get_object_or_404(scope_to_user(Order.objects.all(), request.user), pk=pk)
    form = OrderForm(request.POST or None, instance=order, user=request.user)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("order_detail", pk=order.pk)

    return render(
        request,
        "orders/form.html",
        {
            "form": form,
            "buyer": None,
            "order": order,
            "page_title": "Editar pedido",
            "submit_label": "Guardar cambios",
        },
    )


@login_required
def order_delete(request, pk):
    order = get_object_or_404(
        scope_to_user(
            Order.objects.select_related("buyer", "agent"),
            request.user,
        ),
        pk=pk,
    )

    will_cancel = (
        not can_manage_office(request.user)
        or has_related_records(order)
    )
    if request.method == "POST":
        if will_cancel:
            order.status = "cancelled"
            order.save(update_fields=["status", "updated_at"])
            messages.success(
                request,
                "El pedido se ha cancelado y su historial se conserva.",
            )
        else:
            order.delete()
            messages.success(request, "El pedido se ha eliminado definitivamente.")
        return redirect("order_list")

    return render(
        request,
        "orders/delete.html",
        {"order": order, "will_archive": will_cancel},
    )
