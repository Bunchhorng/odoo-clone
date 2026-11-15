from django.urls import path
from . import views
from . import catalog_transfer
from . import inventory_views
from . import accounting_views
from . import operations_views
from . import location_views

app_name = "business"
urlpatterns = [
    path("warehouses/", location_views.warehouses, name="warehouses"),
    path("warehouses/<int:record_id>/", location_views.warehouse_item, name="warehouse"),
    path("locations/", location_views.locations, name="locations"),
    path("locations/<int:record_id>/", location_views.location_item, name="location"),
    path("helpdesk/", operations_views.tickets, name="helpdesk"),
    path("helpdesk/<int:record_id>/", operations_views.ticket_item, name="ticket"),
    path("helpdesk/<int:record_id>/actions/", operations_views.ticket_actions, name="ticket-actions"),
    path("helpdesk/<int:record_id>/messages/", operations_views.messages, name="ticket-messages"),
    path("timesheets/", operations_views.timesheets, name="timesheets"),
    path("timesheets/export/", operations_views.export_time, name="time-export"),
    path("timesheets/<int:record_id>/", operations_views.time_item, name="time-entry"),
    path("timesheets/<int:record_id>/actions/", operations_views.time_actions, name="time-actions"),
    path("accounting/settings/", accounting_views.settings, name="accounting-settings"),
    path("accounting/sync/", accounting_views.sync, name="accounting-sync"),
    path("accounting/entries/", accounting_views.entries, name="accounting-entries"),
    path("accounting/reports/", accounting_views.reports, name="accounting-reports"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("settings/", views.workspace_settings, name="settings"),
    path("orders/", views.orders, name="orders"),
    path("orders/<int:record_id>/", views.order_item, name="order"),
    path("orders/<int:record_id>/actions/", views.order_action, name="order-action"),
    path("orders/<int:record_id>/receipts/", inventory_views.receipts, name="receipts"),
    path("orders/<int:record_id>/reservations/", inventory_views.reservations, name="reservations"),
    path("orders/<int:record_id>/reservations/release/", inventory_views.release_reservation, name="reservation-release"),
    path("orders/<int:record_id>/operations/", inventory_views.operations, name="operations"),
    path("orders/<int:record_id>/invoices/", views.order_invoices, name="order-invoices"),
    path("operations/<int:record_id>/actions/", inventory_views.operation_action, name="operation-action"),
    path("invoices/", views.invoices, name="invoices"),
    path("invoices/<int:record_id>/", views.invoice_item, name="invoice"),
    path("invoices/<int:record_id>/actions/", views.invoice_action, name="invoice-action"),
    path("invoices/<int:record_id>/payments/", views.payments, name="payments"),
    path("stock/", inventory_views.stock, name="stock"),
    path("stock/<int:record_id>/return/", inventory_views.supplier_return, name="supplier-return"),
    path("stock/<int:record_id>/reverse/", inventory_views.reverse_adjustment, name="reverse-adjustment"),
    path("<str:resource>/export/", catalog_transfer.export_csv, name="catalog-export"),
    path("<str:resource>/import/preview/", catalog_transfer.import_preview, name="catalog-import-preview"),
    path("<str:resource>/import/", catalog_transfer.import_commit, name="catalog-import"),
    path("<str:resource>/bulk/", catalog_transfer.bulk_action, name="catalog-bulk"),
    path("<str:resource>/", views.catalog, name="catalog"),
    path("<str:resource>/<int:record_id>/", views.catalog_item, name="catalog-item"),
]
