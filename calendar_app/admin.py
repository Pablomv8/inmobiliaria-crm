from django.contrib import admin

from .models import (
    Appointment,
    Call,
    CallComment,
    CounterOffer,
    ProposalAppointment,
    ProposalComment,
)

# Register your models here.


admin.site.register(Call)
admin.site.register(Appointment)
admin.site.register(ProposalAppointment)
admin.site.register(ProposalComment)
admin.site.register(CounterOffer)
admin.site.register(CallComment)
