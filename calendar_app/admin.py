from django.contrib import admin

from .models import Appointment, Call, ProposalAppointment

# Register your models here.


admin.site.register(Call)
admin.site.register(Appointment)
admin.site.register(ProposalAppointment)
