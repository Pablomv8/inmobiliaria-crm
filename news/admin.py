from django.contrib import admin
from .models import News, NewsComment
# Register your models here.


admin.site.register(NewsComment)
admin.site.register(News)