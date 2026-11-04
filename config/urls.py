from django.contrib import admin
from django.urls import path

from demo.views import stock_overview

urlpatterns = [
    path("", stock_overview, name="stock-overview"),
    path("admin/", admin.site.urls),
]
