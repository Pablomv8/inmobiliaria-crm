from django.views.generic import ListView
from django.views.generic import CreateView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from django.urls import reverse_lazy

from .models import Sale
from .forms import SaleForm

from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect

from activities.utils import log_activity

from django.db.models import Q
from users.models import User


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
    if agent:

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

    return render(
        request,
        "sales/sale_list.html",
        {
            "sales": sales,
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


class SaleCreateView(CreateView):

    model = Sale

    form_class = SaleForm

    template_name = "sales/sale_form.html"

    success_url = reverse_lazy("sale_list")

    @login_required
    def form_valid(self, form):

        response = super().form_valid(form)

        sale = self.object

        # inmueble vendido

        sale.related_property.status = "sold"
        sale.related_property.save()

        # contacto cerrado

        sale.buyer.status = "closed"
        sale.buyer.save()

        log_activity(
            self.request.user,
            "sale_created",
            f"Registró la venta de '{sale.related_property.full_address}'"
        )

        return response
    

@require_POST
@login_required
def sale_update_status(request, pk):

    sale = get_object_or_404(Sale, pk=pk)

    sale.status = request.POST.get("status")
    sale.save()  # aquí se ejecuta la lógica del modelo

    return redirect("sale_list")
