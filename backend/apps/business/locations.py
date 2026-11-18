"""INV-01 configuration and ledger endpoints; no transfers or reservations.

Writers hold the existing company row lock inside transaction.atomic(). Existing
signed quantities remain the company stock authority. Endpoints describe the same
quantity, never a second movement or an additional opening balance.
"""
from decimal import Decimal
import re

from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import StockLocation, StockMovement, Warehouse

MAX_DEPTH = 32
VIRTUALS = {
    "supplier": ("Suppliers", "SUPPLIERS"),
    "customer": ("Customers", "CUSTOMERS"),
    "inventory": ("Inventory adjustments", "ADJUSTMENTS"),
}


def subtree_ids(location):
    seen, frontier = {location.pk}, {location.pk}
    for _ in range(MAX_DEPTH):
        children = set(StockLocation.objects.filter(company_id=location.company_id, parent_id__in=frontier).values_list("id", flat=True))
        if not children:
            return seen
        if children & seen:
            raise ValidationError("The location hierarchy contains a cycle.")
        seen |= children
        frontier = children
    raise ValidationError(f"Use at most {MAX_DEPTH} levels in the location hierarchy.")


def has_movements(ids):
    return StockMovement.objects.filter(Q(source_location_id__in=ids) | Q(destination_location_id__in=ids)).exists()


def validate_location(location):
    if location.usage not in StockLocation.Usage.values:
        raise ValidationError("Choose a valid location type.")
    previous = StockLocation.objects.filter(pk=location.pk).first() if location.pk else None
    if previous and previous.company_id != location.company_id:
        raise ValidationError("A location cannot be moved to another company.")
    seen = {location.pk} if location.pk else set()
    parent, depth = location.parent if location.parent_id else None, 1
    while parent:
        depth += 1
        if parent.pk in seen:
            raise ValidationError("A location cannot be its own ancestor.")
        seen.add(parent.pk)
        if depth > MAX_DEPTH:
            raise ValidationError(f"Use at most {MAX_DEPTH} levels in the location hierarchy.")
        if parent.company_id != location.company_id:
            raise ValidationError("Parent and child locations must belong to the same company.")
        if location.is_active and not parent.is_active:
            raise ValidationError("An active location requires active ancestors.")
        if depth == 2 and parent.usage not in (StockLocation.Usage.VIEW, location.usage):
            raise ValidationError("Use a grouping parent or a parent of the same location type.")
        parent = parent.parent if parent.parent_id else None
    if not previous:
        return
    if previous.system_key and (not location.is_active or location.parent_id != previous.parent_id or location.usage != previous.usage):
        raise ValidationError("Default posting locations must remain active with their original type and parent.")
    root = Warehouse.objects.filter(stock_location_id=location.pk).first()
    if root and (location.usage != "internal" or location.parent_id or (root.is_active and not location.is_active)):
        raise ValidationError("A warehouse stock location must remain an active internal root while the warehouse is active.")
    if not location.is_active and location.children.filter(is_active=True).exists():
        raise ValidationError("Archive active child locations first.")
    if location.usage != previous.usage and (location.children.exists() or root or has_movements({location.pk})):
        raise ValidationError("A referenced location's type cannot be changed.")
    if location.parent_id != previous.parent_id:
        ids = subtree_ids(previous)
        if root or has_movements(ids):
            raise ValidationError("A warehouse root or a hierarchy with stock history cannot be reparented.")
        # Account for the entire moved subtree, not just the edited node.
        frontier, child_depth = {location.pk}, depth
        while frontier:
            frontier = set(StockLocation.objects.filter(company_id=location.company_id, parent_id__in=frontier).values_list("id", flat=True))
            if frontier:
                child_depth += 1
                if child_depth > MAX_DEPTH:
                    raise ValidationError(f"The moved hierarchy would exceed {MAX_DEPTH} levels.")


def validate_warehouse(warehouse):
    warehouse.code = warehouse_code(warehouse.code)
    location = warehouse.stock_location
    if location.company_id != warehouse.company_id or location.usage != "internal" or location.parent_id:
        raise ValidationError("Choose an internal root location belonging to this company.")
    if warehouse.is_active and not location.is_active:
        raise ValidationError("An active warehouse requires an active stock location.")
    previous = Warehouse.objects.filter(pk=warehouse.pk).first() if warehouse.pk else None
    if previous:
        if previous.company_id != warehouse.company_id or previous.stock_location_id != warehouse.stock_location_id:
            raise ValidationError("Warehouse company and stock location cannot be reassigned.")
        if previous.system_key and not warehouse.is_active:
            raise ValidationError("The default warehouse is required by existing posting APIs and cannot be archived in INV-01.")
        if not warehouse.is_active:
            ids = subtree_ids(location)
            if has_movements(ids):
                raise ValidationError("A warehouse with stock history cannot be archived in INV-01.")


def available_code(model, company_id, base, *, using="default"):
    code, suffix = base, 1
    while model.objects.using(using).filter(company_id=company_id, code=code).exists():
        suffix += 1
        code = f"{base}-{suffix}"
    return code


def ensure_virtuals(company_id, *, using="default"):
    locations = {}
    for usage, (name, code) in VIRTUALS.items():
        location = StockLocation.objects.using(using).filter(company_id=company_id, system_key=usage).first()
        if location is None:
            location = StockLocation.objects.using(using).create(company_id=company_id, name=name,
                code=available_code(StockLocation, company_id, code, using=using), usage=usage, system_key=usage)
        locations[usage] = location
    return locations


def ensure_defaults(company_id, *, using="default"):
    virtuals = ensure_virtuals(company_id, using=using)
    warehouse = Warehouse.objects.using(using).filter(company_id=company_id, system_key="default").select_related("stock_location").first()
    if warehouse is None:
        code = available_code(Warehouse, company_id, "WH", using=using)
        location = StockLocation.objects.using(using).create(company_id=company_id, name="Main warehouse stock",
            code=available_code(StockLocation, company_id, f"{code}/STOCK", using=using), usage="internal", system_key="stock")
        warehouse = Warehouse.objects.using(using).create(company_id=company_id, name="Main Warehouse", code=code,
            stock_location=location, system_key="default")
    if not warehouse.is_active or not warehouse.stock_location.is_active or warehouse.stock_location.usage != "internal":
        raise ValidationError("The default warehouse and stock location must be active before posting stock.")
    return warehouse.stock_location, virtuals


def assign_movement_locations(movement, *, using="default"):
    # Corrections always reverse the original endpoints, including historical rows.
    original_id = movement.return_of_id or movement.reversal_of_id
    if original_id:
        original = StockMovement.objects.using(using).filter(pk=original_id, company_id=movement.company_id).first()
        if original is None:
            raise ValidationError("The corrected stock movement must belong to this company.")
        movement.source_location_id = original.destination_location_id
        movement.destination_location_id = original.source_location_id
        return
    stock, virtuals = ensure_defaults(movement.company_id, using=using)
    order_kind = movement.order.kind if movement.order_id else None
    external = virtuals["supplier" if order_kind == "purchase" else "customer" if order_kind == "sale" else "inventory"]
    source, destination = (external, stock) if Decimal(movement.quantity) >= 0 else (stock, external)
    movement.source_location, movement.destination_location = source, destination


def validate_movement_locations(movement):
    if not movement.source_location_id or not movement.destination_location_id:
        raise ValidationError("Both source and destination locations are required.")
    source, destination = movement.source_location, movement.destination_location
    if source.pk == destination.pk:
        raise ValidationError("Source and destination locations must differ.")
    if any(location.company_id != movement.company_id for location in (source, destination)) or movement.product.company_id != movement.company_id:
        raise ValidationError("A stock movement, product and both locations must belong to the same company.")
    if movement.order_id and movement.order.company_id != movement.company_id:
        raise ValidationError("The stock document must belong to the movement's company.")
    if movement.order_line_id and (movement.order_line.order_id != movement.order_id or movement.order_line.product_id != movement.product_id):
        raise ValidationError("The stock line must belong to the same order and product.")
    if movement.receipt_id and (movement.receipt.company_id != movement.company_id or movement.receipt.order_id != movement.order_id):
        raise ValidationError("The receipt must belong to the same company and order.")
    quantity = Decimal(movement.quantity)
    if (source.usage == "view" or destination.usage == "view" or
            (source.usage == "internal") == (destination.usage == "internal") or
            (quantity > 0 and destination.usage != "internal") or (quantity < 0 and source.usage != "internal")):
        raise ValidationError("INV-01 requires one internal endpoint matching the signed stock quantity; transfers are not implemented.")
    if not source.is_active or not destination.is_active:
        raise ValidationError("Stock posting requires active locations.")


def warehouse_code(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,15}", value.strip()):
        raise ValidationError("Warehouse code must start with a letter and contain at most 16 letters, digits, hyphens or underscores.")
    return value.strip().upper()
