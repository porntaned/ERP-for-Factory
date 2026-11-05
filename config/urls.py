from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from demo import production_views, views

urlpatterns = [
    path("", views.stock_overview, name="stock-overview"),
    path("receipts/new/", views.receipt_new, name="receipt-new"),
    path("transfers/new/", views.transfer_new, name="transfer-new"),
    path("history/", views.history, name="history"),
    path("production/", production_views.production_list, name="production-list"),
    path("production/<int:pk>/", production_views.production_detail, name="production-detail"),
    path("lots/<int:pk>/genealogy/", production_views.lot_genealogy, name="lot-genealogy"),
    path("reversals/receipt/<int:pk>/", views.reverse, {"kind": "receipt"}, name="reverse-receipt"),
    path(
        "reversals/transfer/<int:pk>/", views.reverse, {"kind": "transfer"}, name="reverse-transfer"
    ),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="demo/login.html"),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
]
