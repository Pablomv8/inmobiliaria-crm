from django.contrib import admin
from .models import Listing, ListingComment

# Register your models here.

admin.site.register(Listing)
admin.site.register(ListingComment)
