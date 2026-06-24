from django.shortcuts import render

# Create your views here.
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Activity
from users.models import User


class ActivityListView(LoginRequiredMixin, ListView):

    model = Activity

    template_name = "activities/activity_list.html"

    context_object_name = "activities"

    paginate_by = 30

    def get_queryset(self):

        qs = Activity.objects.select_related(
            "user"
        )

        user = self.request.user

        # agente -> solo su actividad
        if user.role == "agent":

            qs = qs.filter(
                user=user
            )

        activity_type = self.request.GET.get("action")

        if activity_type:

            qs = qs.filter(
                action=activity_type
            )

        selected_user = self.request.GET.get("user")

        if selected_user and user.role in ["admin", "manager"]:

            qs = qs.filter(
                user_id=selected_user
            )

        return qs

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        if self.request.user.role in ["admin", "manager"]:

            context["users"] = User.objects.filter(
                role="agent"
            )

        return context
    

    
    
    