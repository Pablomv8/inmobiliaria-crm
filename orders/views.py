from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from contacts.models import Contact
from properties.models import Property, Zone

from .forms import OrderCommentForm, OrderForm
from .models import Order


@login_required
def order_list(request):
    orders = Order.objects.select_related(
        "buyer",
        "buyer__assigned_agent",
        "zone",
    )
    search = request.GET.get("search", "").strip()
    payment_type = request.GET.get("payment_type", "")
    property_type = request.GET.get("property_type", "")
    zone = request.GET.get("zone", "")

    if search:
        orders = orders.filter(
            Q(buyer__name__icontains=search)
            | Q(buyer__last_name__icontains=search)
            | Q(buyer__phone__icontains=search)
        )
    if payment_type:
        orders = orders.filter(payment_type=payment_type)
    if property_type:
        orders = orders.filter(property_type=property_type)
    if zone:
        orders = orders.filter(zone_id=zone)

    return render(
        request,
        "orders/list.html",
        {
            "orders": orders,
            "payment_choices": Order.PAYMENT_TYPE_CHOICES,
            "property_type_choices": Property.PROPERTY_TYPE_CHOICES,
            "zones": Zone.objects.all(),
        },
    )


@login_required
def order_create(request, buyer_id=None):
    buyer = None
    if buyer_id is not None:
        buyer = get_object_or_404(
            Contact,
            pk=buyer_id,
            contact_type="buyer",
        )

    form = OrderForm(request.POST or None, buyer_obj=buyer)
    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)
        if buyer is not None:
            order.buyer = buyer
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
        Order.objects.select_related(
            "buyer",
            "buyer__assigned_agent",
            "zone",
        ),
        pk=pk,
    )
    sale_appointments = order.sale_appointments.select_related(
        "listing__property",
        "agent",
    ).filter(appointment_type="sale").order_by("-date", "-time")
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
        Order.objects.select_related(
            "buyer",
            "buyer__assigned_agent",
            "zone",
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
    ).filter(appointment_type="sale").order_by("-date", "-time")
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
    order = get_object_or_404(Order, pk=pk)
    form = OrderForm(request.POST or None, instance=order)

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
    order = get_object_or_404(Order.objects.select_related("buyer"), pk=pk)

    if request.method == "POST":
        order.delete()
        return redirect("order_list")

    return render(request, "orders/delete.html", {"order": order})
