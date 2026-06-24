from django.contrib import admin

from .models import Call, Appointment

# Register your models here.


admin.site.register(Call)
admin.site.register(Appointment)