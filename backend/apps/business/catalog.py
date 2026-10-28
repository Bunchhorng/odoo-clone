from decimal import Decimal

from django.db import models
from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce

from apps.companies.models import CompanyMembership
from apps.core.api import APIError
from .models import Contact, Opportunity, Product, ProductCategory, Project, Task
from .services import date_value, decimal_value, positive_id, scoped

# Explicit field lists keep company IDs, totals, and document states out of generic writes.
CATALOG = {
    "contacts": (Contact, ["name", "organization", "email", "phone", "address", "country", "is_customer", "is_supplier", "notes", "is_active"]),
    "products": (Product, ["name", "sku", "category_id", "barcode", "kind", "sale_price", "cost_price", "unit", "reorder_level", "notes", "is_active"]),
    "product-categories": (ProductCategory, ["name", "is_active"]),
    "opportunities": (Opportunity, ["title", "contact_id", "stage", "expected_revenue", "probability", "expected_date", "notes", "is_active"]),
    "projects": (Project, ["name", "contact_id", "notes", "is_active"]),
    "tasks": (Task, ["title", "project_id", "assignee_id", "stage", "priority", "due_date", "notes", "is_active"]),
}


def definition(resource):
    if resource not in CATALOG:
        raise APIError("Resource not found.", 404)
    return CATALOG[resource]


def catalog_queryset(resource, company_id):
    model, _ = definition(resource)
    queryset = model.objects.filter(company_id=company_id)
    if resource == "products":
        queryset = queryset.select_related("category").annotate(stock_quantity=Coalesce(
            Sum("movements__quantity"), Value(Decimal("0")),
            output_field=DecimalField(max_digits=20, decimal_places=3),
        ))
    if resource in ("opportunities", "projects"):
        queryset = queryset.select_related("contact")
    if resource == "tasks":
        queryset = queryset.select_related("project", "assignee")
    return queryset


def filtered_catalog(resource, company_id, params):
    queryset = catalog_queryset(resource, company_id)
    active = params.get("active", "true")
    if active not in ("true", "false", "all"):
        raise APIError("Active filter must be true, false, or all.")
    if active != "all":
        queryset = queryset.filter(is_active=active == "true")
    query = params.get("q", "").strip()[:200]
    if query:
        predicate = Q(**{"title__icontains" if resource in ("opportunities", "tasks") else "name__icontains": query})
        if resource == "contacts":
            predicate |= Q(email__icontains=query) | Q(organization__icontains=query) | Q(phone__icontains=query)
        if resource == "products":
            predicate |= Q(sku__icontains=query) | Q(barcode__icontains=query) | Q(category__name__icontains=query)
        queryset = queryset.filter(predicate)
    if resource == "contacts":
        role = params.get("role", "all")
        if role not in ("all", "customer", "supplier", "both"):
            raise APIError("Choose all, customer, supplier, or both for contact role.")
        if role in ("customer", "both"):
            queryset = queryset.filter(is_customer=True)
        if role in ("supplier", "both"):
            queryset = queryset.filter(is_supplier=True)
    if resource == "products":
        kind = params.get("kind", "all")
        if kind not in ("all", "goods", "service"):
            raise APIError("Choose all, goods, or service for product type.")
        if kind != "all":
            queryset = queryset.filter(kind=kind)
        category = params.get("category_id", "")
        if category == "none":
            queryset = queryset.filter(category__isnull=True)
        elif category:
            queryset = queryset.filter(category=scoped(ProductCategory, company_id, category))
        stock = params.get("stock", "all")
        if stock not in ("all", "low", "out"):
            raise APIError("Choose all, low, or out for stock filter.")
        if stock != "all":
            queryset = queryset.filter(kind="goods", **(
                {"stock_quantity__lte": 0} if stock == "out" else {"stock_quantity__lte": F("reorder_level")}
            ))
    if resource in ("opportunities", "tasks") and params.get("stage"):
        queryset = queryset.filter(stage=params["stage"])
    if resource == "tasks" and params.get("project_id"):
        queryset = queryset.filter(project=scoped(Project, company_id, params["project_id"]))
    ordering = params.get("ordering", "-id")
    allowed = {"id", "updated_at", "title" if resource in ("opportunities", "tasks") else "name"}
    if resource == "contacts":
        allowed |= {"organization", "email", "phone"}
    if resource == "products":
        allowed |= {"sku", "sale_price", "cost_price", "stock_quantity", "category__name", "barcode"}
    if ordering.removeprefix("-") not in allowed:
        raise APIError("Choose a supported sort field.")
    return queryset.order_by(ordering, "id")


def catalog_data(resource, item):
    _, fields = definition(resource)
    data = {key: getattr(item, key) for key in fields}
    data.update(id=item.pk, created_at=item.created_at, updated_at=item.updated_at)
    if resource == "products":
        data["stock_quantity"] = item.stock_quantity or 0
        data["category_name"] = item.category.name if item.category_id else ""
        data["barcode"] = item.barcode or ""
    if resource in ("opportunities", "projects"):
        data["contact_name"] = item.contact.name if item.contact_id else ""
    if resource == "tasks":
        data["project_name"] = item.project.name
        data["assignee_name"] = item.assignee.get_full_name() or item.assignee.email if item.assignee_id else "Unassigned"
    return data


def prepare_catalog(resource, company_id, data, item=None):
    model, allowed = definition(resource)
    if not isinstance(data, dict) or not data or set(data) - set(allowed):
        raise APIError("Provide supported fields for this record.")
    item = item or model(company_id=company_id)
    old_kind = item.kind if resource == "products" and item.pk else None
    for key, value in data.items():
        field = model._meta.get_field(key[:-3] if key.endswith("_id") else key)
        if isinstance(field, models.ForeignKey):
            # Historical assignments can become inactive; retaining one is not a new grant.
            # Check company ownership even when retaining it, then enforce active status
            # only when a relationship is newly selected or changed.
            if value in (None, "") and field.null:
                value = None
            elif key == "assignee_id":
                value = positive_id(value)
                unchanged = bool(item.pk and getattr(item, key) == value)
                if not unchanged and not CompanyMembership.objects.filter(company_id=company_id, user_id=value, is_active=True, user__is_active=True).exists():
                    raise APIError("Choose an active teammate in this company.")
            else:
                related = scoped(field.related_model, company_id, value)
                unchanged = bool(item.pk and getattr(item, key) == related.pk)
                if not unchanged and not related.is_active:
                    raise APIError("Choose an active related record.")
                value = related.pk
        elif isinstance(field, models.BooleanField):
            if not isinstance(value, bool):
                raise APIError(f"{key} must be true or false.")
        elif isinstance(field, models.DecimalField):
            value = decimal_value(value, field.verbose_name, places=field.decimal_places,
                                  maximum=Decimal(10) ** (field.max_digits - field.decimal_places) - Decimal(1).scaleb(-field.decimal_places))
        elif isinstance(field, models.IntegerField):
            if isinstance(value, bool) or not isinstance(value, int):
                raise APIError(f"{key} must be a whole number.")
        elif isinstance(field, models.DateField):
            value = date_value(value, key, optional=field.null)
        else:
            if not isinstance(value, str):
                raise APIError(f"{key} must be text.")
            value = value.strip()
        setattr(item, key, value)
    if resource == "products":
        item.sku = item.sku.upper()
        item.barcode = item.barcode or None
        if old_kind and item.kind != old_kind and (item.movements.exists() or item.orderline_set.exists()):
            raise APIError("A product's type cannot change after it has stock movements or order lines.", 409)
    if resource == "opportunities" and item.stage in ("won", "lost"):
        item.probability = 100 if item.stage == "won" else 0
    if resource == "contacts" and not (item.is_customer or item.is_supplier):
        raise APIError("A contact must be a customer, a supplier, or both.")
    item.full_clean()
    return item


def save_catalog(resource, company_id, data, item=None):
    item = prepare_catalog(resource, company_id, data, item)
    item.save()
    return catalog_queryset(resource, company_id).get(pk=item.pk)
