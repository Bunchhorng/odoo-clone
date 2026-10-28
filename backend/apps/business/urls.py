from django.urls import path
from . import views
from . import catalog_transfer

app_name = "business"
urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("settings/", views.workspace_settings, name="settings"),
    path("orders/", views.orders, name="orders"),
    path("orders/<int:record_id>/", views.order_item, name="order"),
    path("orders/<int:record_id>/actions/", views.order_action, name="order-action"),
    path("invoices/", views.invoices, name="invoices"),
    path("invoices/<int:record_id>/", views.invoice_item, name="invoice"),
    path("invoices/<int:record_id>/actions/", views.invoice_action, name="invoice-action"),
    path("invoices/<int:record_id>/payments/", views.payments, name="payments"),
    path("stock/", views.stock, name="stock"),
    path("<str:resource>/export/", catalog_transfer.export_csv, name="catalog-export"),
    path("<str:resource>/import/preview/", catalog_transfer.import_preview, name="catalog-import-preview"),
    path("<str:resource>/import/", catalog_transfer.import_commit, name="catalog-import"),
    path("<str:resource>/bulk/", catalog_transfer.bulk_action, name="catalog-bulk"),
    path("<str:resource>/", views.catalog, name="catalog"),
    path("<str:resource>/<int:record_id>/", views.catalog_item, name="catalog-item"),
]
