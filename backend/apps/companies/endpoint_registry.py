"""Single source of truth for API endpoint permission classification.

The registry is intentionally declarative: decorators, audit logging and route
coverage tests all consult this module instead of maintaining separate maps.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable


PUBLIC_PREFIXES = ("admin/", "api/v1/auth/", "api/v1/health/")


@dataclass(frozen=True)
class EndpointRule:
    app_key: str | Callable
    action: str | Callable
    owner_only: bool = False
    membership_only: bool = False
    extra: tuple[tuple[str, str], ...] = ()

    def resolve(self, request, kwargs):
        app_key = self.app_key(request, kwargs) if callable(self.app_key) else self.app_key
        action = self.action(request, kwargs) if callable(self.action) else self.action
        return app_key, action


def _json_action(request, default="approve"):
    try:
        value = json.loads(request.body or b"{}").get("action", default)
        return value if isinstance(value, str) else default
    except (TypeError, ValueError, UnicodeDecodeError):
        return default


def _catalog_app(request, kwargs):
    return {
        "departments": "human-resources", "employees": "human-resources",
        "opportunities": "crm", "projects": "projects",
    }.get(kwargs.get("resource"), kwargs.get("resource"))


def _method_action(request, _kwargs):
    return {"GET": "read", "POST": "create", "PATCH": "write", "DELETE": "delete"}[request.method]


def _order_app(request, kwargs):
    """Lists use ?kind; detail routes look up kind later during enforcement."""
    kind = request.GET.get("kind")
    if kind == "purchase":
        return "purchase"
    if not kind:
        # The unqualified list contains both order kinds.  It is legitimate for
        # either preset to open it; the query layer scopes the returned kinds.
        return ("sales", "purchase")
    return "sales"


def _approval_action(request, _kwargs):
    return "approve" if _json_action(request) in {"confirm", "cancel", "approve", "reject", "void", "validate", "close", "assign"} else "write"


def _ticket_action(request, _kwargs):
    return "approve" if _json_action(request) in {"assign", "close", "resolve", "cancel"} else "write"


def _timesheet_action(request, _kwargs):
    return "approve" if _json_action(request) in {"approve", "reject", "void"} else "write"


# Key format: fully qualified decorated view name, HTTP method.  Dynamic
# resource/order rules are resolved by the small functions above.
ENDPOINT_REGISTRY = {
    ("apps.companies.views.companies", "GET"): EndpointRule("companies", "read"),
    ("apps.companies.views.companies", "POST"): EndpointRule("companies", "create"),
    ("apps.companies.views.select_company", "POST"): EndpointRule("companies", "read", membership_only=True),
    ("apps.companies.views.members", "GET"): EndpointRule("team", "read"),
    ("apps.companies.views.members", "POST"): EndpointRule("team", "write"),
    ("apps.companies.views.update_member", "PATCH"): EndpointRule("team", "write"),
    ("apps.business.views.catalog", "GET"): EndpointRule(_catalog_app, "read"),
    ("apps.business.views.catalog", "POST"): EndpointRule(_catalog_app, "create"),
    ("apps.business.views.catalog_item", "GET"): EndpointRule(_catalog_app, "read"),
    ("apps.business.views.catalog_item", "PATCH"): EndpointRule(_catalog_app, "write"),
    ("apps.business.catalog_transfer.export_csv", "GET"): EndpointRule(_catalog_app, "read"),
    ("apps.business.catalog_transfer.import_preview", "POST"): EndpointRule(_catalog_app, "create"),
    ("apps.business.catalog_transfer.import_commit", "POST"): EndpointRule(_catalog_app, "create"),
    ("apps.business.catalog_transfer.bulk_action", "POST"): EndpointRule(_catalog_app, "write"),
    ("apps.business.views.orders", "GET"): EndpointRule(_order_app, "read"),
    ("apps.business.views.orders", "POST"): EndpointRule(_order_app, "create"),
    ("apps.business.views.order_item", "GET"): EndpointRule(_order_app, "read"),
    ("apps.business.views.order_item", "PATCH"): EndpointRule(_order_app, "write"),
    ("apps.business.views.order_action", "POST"): EndpointRule(_order_app, _approval_action),
    ("apps.business.views.order_invoices", "GET"): EndpointRule(_order_app, "read"),
    ("apps.business.views.order_invoices", "POST"): EndpointRule(_order_app, "read", extra=(("invoicing", "create"),)),
    ("apps.business.views.invoices", "GET"): EndpointRule("invoicing", "read"),
    ("apps.business.views.invoice_item", "GET"): EndpointRule("invoicing", "read"),
    ("apps.business.views.invoice_item", "PATCH"): EndpointRule("invoicing", "write"),
    ("apps.business.views.invoice_action", "POST"): EndpointRule("invoicing", _approval_action),
    ("apps.business.views.payments", "POST"): EndpointRule("invoicing", "approve"),
    ("apps.business.views.workspace_settings", "GET"): EndpointRule("settings", "read"),
    ("apps.business.views.workspace_settings", "PATCH"): EndpointRule("settings", "write"),
    ("apps.business.views.dashboard", "GET"): EndpointRule("dashboard", "read"),
    ("apps.business.accounting_views.settings", "GET"): EndpointRule("accounting", "read"),
    ("apps.business.accounting_views.settings", "PATCH"): EndpointRule("accounting", "write", owner_only=True),
    ("apps.business.accounting_views.sync", "POST"): EndpointRule("accounting", "write"),
    ("apps.business.accounting_views.entries", "GET"): EndpointRule("accounting", "read"),
    ("apps.business.accounting_views.reports", "GET"): EndpointRule("accounting", "read"),
    ("apps.business.operations_views.tickets", "GET"): EndpointRule("helpdesk", "read"),
    ("apps.business.operations_views.tickets", "POST"): EndpointRule("helpdesk", "create"),
    ("apps.business.operations_views.ticket_item", "GET"): EndpointRule("helpdesk", "read"),
    ("apps.business.operations_views.ticket_item", "PATCH"): EndpointRule("helpdesk", "write"),
    ("apps.business.operations_views.ticket_actions", "POST"): EndpointRule("helpdesk", _ticket_action),
    ("apps.business.operations_views.messages", "GET"): EndpointRule("helpdesk", "read"),
    ("apps.business.operations_views.messages", "POST"): EndpointRule("helpdesk", "create"),
    ("apps.business.operations_views.timesheets", "GET"): EndpointRule("timesheets", "read"),
    ("apps.business.operations_views.timesheets", "POST"): EndpointRule("timesheets", "create"),
    ("apps.business.operations_views.time_item", "GET"): EndpointRule("timesheets", "read"),
    ("apps.business.operations_views.time_item", "PATCH"): EndpointRule("timesheets", "write"),
    ("apps.business.operations_views.time_actions", "POST"): EndpointRule("timesheets", _timesheet_action),
    ("apps.business.operations_views.export_time", "GET"): EndpointRule("timesheets", "read"),
    ("apps.business.location_views.warehouses", "GET"): EndpointRule("inventory", "read"),
    ("apps.business.location_views.warehouses", "POST"): EndpointRule("inventory", "create"),
    ("apps.business.location_views.warehouse_item", "GET"): EndpointRule("inventory", "read"),
    ("apps.business.location_views.warehouse_item", "PATCH"): EndpointRule("inventory", "write"),
    ("apps.business.location_views.warehouse_item", "DELETE"): EndpointRule("inventory", "delete"),
    ("apps.business.location_views.locations", "GET"): EndpointRule("inventory", "read"),
    ("apps.business.location_views.locations", "POST"): EndpointRule("inventory", "create"),
    ("apps.business.location_views.location_item", "GET"): EndpointRule("inventory", "read"),
    ("apps.business.location_views.location_item", "PATCH"): EndpointRule("inventory", "write"),
    ("apps.business.location_views.location_item", "DELETE"): EndpointRule("inventory", "delete"),
    ("apps.business.inventory_views.receipts", "GET"): EndpointRule("purchase", "read"),
    ("apps.business.inventory_views.receipts", "POST"): EndpointRule("purchase", "approve"),
    ("apps.business.inventory_views.reservations", "GET"): EndpointRule("sales", "read"),
    ("apps.business.inventory_views.reservations", "POST"): EndpointRule("sales", "approve"),
    ("apps.business.inventory_views.release_reservation", "POST"): EndpointRule("sales", "approve"),
    ("apps.business.inventory_views.operations", "GET"): EndpointRule("inventory", "read"),
    ("apps.business.inventory_views.operations", "POST"): EndpointRule("inventory", "create"),
    ("apps.business.inventory_views.operation_action", "POST"): EndpointRule("inventory", "approve"),
    ("apps.business.inventory_views.transfers", "GET"): EndpointRule("inventory", "read"),
    ("apps.business.inventory_views.transfers", "POST"): EndpointRule("inventory", "create"),
    ("apps.business.inventory_views.transfer_action", "POST"): EndpointRule("inventory", "approve"),
    ("apps.business.inventory_views.customer_returns", "GET"): EndpointRule("sales", "read"),
    ("apps.business.inventory_views.customer_returns", "POST"): EndpointRule("sales", "create"),
    ("apps.business.inventory_views.customer_return_action", "POST"): EndpointRule("sales", "approve"),
    ("apps.business.inventory_views.stock", "GET"): EndpointRule("inventory", "read"),
    ("apps.business.inventory_views.stock", "POST"): EndpointRule("inventory", "write"),
    ("apps.business.inventory_views.supplier_return", "POST"): EndpointRule("inventory", "approve"),
    ("apps.business.inventory_views.reverse_adjustment", "POST"): EndpointRule("inventory", "approve"),
}


def view_key(view):
    return f"{view.__module__}.{view.__name__}"


def rule_for(view, method):
    return ENDPOINT_REGISTRY.get((view_key(view), method))


def registered_methods(view):
    """Methods declared by this registry, independent of view metadata."""
    key = view_key(view)
    return tuple(method for candidate, method in ENDPOINT_REGISTRY if candidate == key)


def is_explicitly_public(path):
    return path.lstrip("/").startswith(PUBLIC_PREFIXES)
