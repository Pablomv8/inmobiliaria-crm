from django.views.generic import ListView
from django.views.generic import CreateView

from django.urls import reverse_lazy

from .models import Sale
from .forms import SaleForm

from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect

from activities.utils import log_activity


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
            f"Registró la venta de '{sale.related_property.title}'"
        )

        return response
    

@require_POST
def sale_update_status(request, pk):

    sale = get_object_or_404(Sale, pk=pk)

    sale.status = request.POST.get("status")
    sale.save()  # aquí se ejecuta la lógica del modelo

    return redirect("sale_list")