"""Company-scoped INV-01 CRUD. DELETE archives; there is no hard-delete API."""
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse

from apps.companies.access import membership_for
from apps.core.api import APIError, api, json_body, text_field
from .locations import ensure_virtuals, subtree_ids, warehouse_code
from .models import StockLocation, Warehouse
from .services import record_activity, scoped, write_access
from .views import page


def active_flag(data, default=True):
    value = data.get("is_active", default)
    if not isinstance(value, bool):
        raise APIError("Active state must be true or false.")
    return value


def filtered(request, queryset):
    active = request.GET.get("active", "true")
    if active not in ("true", "false", "all"):
        raise APIError("Choose true, false, or all for active records.")
    if active != "all":
        queryset = queryset.filter(is_active=active == "true")
    query = request.GET.get("q", "").strip()[:200]
    if query:
        queryset = queryset.filter(Q(name__icontains=query) | Q(code__icontains=query))
    return queryset


def location_data(item):
    warehouse = getattr(item, "warehouse", None)
    return {"id": item.pk, "company_id": item.company_id, "name": item.name, "code": item.code,
        "usage": item.usage, "parent_id": item.parent_id, "parent_name": item.parent.name if item.parent_id else "",
        "parent_code": item.parent.code if item.parent_id else "", "is_active": item.is_active,
        "is_system": bool(item.system_key), "warehouse_id": warehouse.pk if warehouse else None,
        "warehouse_active": warehouse.is_active if warehouse else False,
        "created_at": item.created_at, "updated_at": item.updated_at}


def warehouse_data(item):
    return {"id": item.pk, "company_id": item.company_id, "name": item.name, "code": item.code,
        "stock_location_id": item.stock_location_id, "stock_location_name": item.stock_location.name,
        "stock_location_code": item.stock_location.code, "is_active": item.is_active,
        "is_default": item.system_key == "default", "created_at": item.created_at, "updated_at": item.updated_at}


def save_location(company_id, data, item=None):
    item = item or StockLocation(company_id=company_id)
    for key, maximum in (("name", 100), ("code", 64)):
        if key in data or not item.pk:
            setattr(item, key, text_field(data, key, maximum=maximum))
    if "usage" in data:
        item.usage = data["usage"]
    if "parent_id" in data:
        item.parent = scoped(StockLocation, company_id, data["parent_id"]) if data["parent_id"] is not None else None
    item.is_active = active_flag(data, item.is_active)
    item.full_clean()
    item.save()
    return item


def save_warehouse(company_id, data, item=None):
    item = item or Warehouse(company_id=company_id)
    creating = not item.pk
    if "name" in data or creating:
        item.name = text_field(data, "name", maximum=100)
    if "code" in data or creating:
        item.code = warehouse_code(data.get("code"))
    item.is_active = active_flag(data, item.is_active)
    if creating:
        if data.get("stock_location_id") is not None:
            item.stock_location = scoped(StockLocation, company_id, data["stock_location_id"])
        else:
            location = StockLocation(company_id=company_id, name=f"{item.name} stock"[:100], code=f"{item.code}/STOCK", usage="internal")
            location.full_clean()
            location.save()
            item.stock_location = location
        if not Warehouse.objects.filter(company_id=company_id, system_key="default").exists():
            if not item.is_active:
                raise APIError("The first warehouse becomes the default and must be active.")
            item.system_key = "default"
            item.stock_location.system_key = "stock"
            item.stock_location.save(update_fields=["system_key"])
        ensure_virtuals(company_id)
    elif "stock_location_id" in data:
        item.stock_location = scoped(StockLocation, company_id, data["stock_location_id"])
    item.full_clean()
    item.save()
    return item


@api(["GET", "POST"])
def warehouses(request, company_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        return page(request, filtered(request, Warehouse.objects.filter(company_id=company_id).select_related("stock_location")), warehouse_data)
    with transaction.atomic():
        write_access(request.user, company_id)
        item = save_warehouse(company_id, json_body(request, {"name", "code", "stock_location_id", "is_active"}))
        record_activity(request.user, company_id, "warehouses", item, f"Created warehouse {item.code}")
        return JsonResponse(warehouse_data(item), status=201)


@api(["GET", "PATCH", "DELETE"])
def warehouse_item(request, company_id, record_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        return JsonResponse(warehouse_data(scoped(Warehouse, company_id, record_id)))
    with transaction.atomic():
        write_access(request.user, company_id)
        item = scoped(Warehouse, company_id, record_id)
        data = {"is_active": False} if request.method == "DELETE" else json_body(request, {"name", "code", "stock_location_id", "is_active"})
        item = save_warehouse(company_id, data, item)
        record_activity(request.user, company_id, "warehouses", item, f"Updated warehouse {item.code}")
        return JsonResponse(warehouse_data(item))


@api(["GET", "POST"])
def locations(request, company_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        queryset = filtered(request, StockLocation.objects.filter(company_id=company_id).select_related("parent", "warehouse"))
        usage = request.GET.get("usage", "")
        if usage:
            if usage not in StockLocation.Usage.values:
                raise APIError("Choose a valid location type.")
            queryset = queryset.filter(usage=usage)
        if "parent_id" in request.GET:
            parent = request.GET["parent_id"]
            queryset = queryset.filter(parent=None if parent == "none" else scoped(StockLocation, company_id, parent))
        if request.GET.get("warehouse_id"):
            warehouse = scoped(Warehouse, company_id, request.GET["warehouse_id"])
            queryset = queryset.filter(pk__in=subtree_ids(warehouse.stock_location))
        return page(request, queryset, location_data)
    with transaction.atomic():
        write_access(request.user, company_id)
        item = save_location(company_id, json_body(request, {"name", "code", "usage", "parent_id", "is_active"}))
        record_activity(request.user, company_id, "locations", item, f"Created location {item.code}")
        return JsonResponse(location_data(item), status=201)


@api(["GET", "PATCH", "DELETE"])
def location_item(request, company_id, record_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        return JsonResponse(location_data(scoped(StockLocation, company_id, record_id)))
    with transaction.atomic():
        write_access(request.user, company_id)
        item = scoped(StockLocation, company_id, record_id)
        data = {"is_active": False} if request.method == "DELETE" else json_body(request, {"name", "code", "usage", "parent_id", "is_active"})
        item = save_location(company_id, data, item)
        record_activity(request.user, company_id, "locations", item, f"Updated location {item.code}")
        return JsonResponse(location_data(item))
