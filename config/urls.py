from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from demo import production_views, quality_views, views

urlpatterns = [
    path("", views.stock_overview, name="stock-overview"),
    path("receipts/new/", views.receipt_new, name="receipt-new"),
    path("transfers/new/", views.transfer_new, name="transfer-new"),
    path("history/", views.history, name="history"),
    path("production/", production_views.production_list, name="production-list"),
    path("production/new/", production_views.production_new, name="production-new"),
    path("production/<int:pk>/", production_views.production_detail, name="production-detail"),
    path(
        "production/<int:pk>/<str:action>/",
        production_views.order_action,
        name="production-action",
    ),
    path(
        "production/<int:pk>/reverse/<int:link_pk>/",
        production_views.reverse_posting,
        name="production-reverse",
    ),
    path("lots/<int:pk>/genealogy/", production_views.lot_genealogy, name="lot-genealogy"),
    path("lots/search/", production_views.lot_search, name="lot-search"),
    path("lots/<int:pk>/trace/", production_views.lot_trace, name="lot-trace"),
    path("quality/", quality_views.quality_list, name="quality-list"),
    path("quality/inspect/", quality_views.inspect, name="quality-inspect"),
    path("quality/return/", quality_views.return_to_hold, name="quality-return"),
    path("quality/audit/", quality_views.quality_audit, name="quality-audit"),
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
