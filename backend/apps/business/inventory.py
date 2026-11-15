"""Stock ledger writes. Call only after write_access inside a company transaction."""
import hashlib
import json
from decimal import Decimal
from uuid import UUID, uuid4

from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.core.api import APIError, text_field
from .locations import ensure_defaults
from .models import Product, PurchaseReceipt, StockMovement, StockReservation, StockOperation, StockOperationLine
from .services import ZERO, check_version, decimal_value, next_number, positive_id, record_activity, scoped, stock_for

MAX_QUANTITY = Decimal("999999999.999")


def reserve_sale(order, user, data):
    """Reserve confirmed-sale goods at the current default internal location."""
    if order.kind != "sale" or order.status != "confirmed":
        raise APIError("Only confirmed sales orders can reserve stock.", 409)
    request_id = request_uuid(data, required=True)
    raw = data.get("lines")
    if not isinstance(raw, list) or not raw:
        raise APIError("Choose one or more goods lines to reserve.")
    requested = {}
    for item in raw:
        if not isinstance(item, dict) or set(item) != {"line_id", "quantity"}:
            raise APIError("Each reservation line needs only line_id and quantity.")
        line_id = positive_id(item["line_id"])
        if line_id in requested:
            raise APIError("Each sales line may appear only once in a reservation.")
        requested[line_id] = decimal_value(item["quantity"], "Reservation quantity", places=3,
            minimum=Decimal("0.001"), maximum=MAX_QUANTITY)
    existing = list(StockReservation.objects.filter(request_id=request_id).select_related("order_line"))
    if existing:
        existing_lines = {row.order_line_id: row.quantity for row in existing}
        if (any(row.company_id != order.company_id or row.order_line.order_id != order.pk for row in existing)
                or existing_lines != requested):
            raise APIError("This reservation request was already used with different details.", 409)
        return existing, False
    location, _ = ensure_defaults(order.company_id)
    lines = {line.pk: line for line in order.lines.select_related("product").filter(product_kind="goods")}
    if set(requested) - set(lines):
        raise APIError("Choose goods lines belonging to this sales order.")
    rows = []
    for line_id, quantity in requested.items():
        line = lines[line_id]
        active_line = StockReservation.objects.filter(order_line=line, state="active").aggregate(value=Sum("quantity"))["value"] or ZERO
        if quantity + active_line > line.quantity:
            raise APIError(f"The reservation exceeds the remaining quantity for {line.description}.", 409)
        on_hand = StockMovement.objects.filter(product=line.product).filter(Q(source_location=location) | Q(destination_location=location)).aggregate(value=Sum("quantity"))["value"] or ZERO
        active_product = StockReservation.objects.filter(product=line.product, location=location, state="active").aggregate(value=Sum("quantity"))["value"] or ZERO
        if quantity > on_hand - active_product:
            raise APIError(f"Insufficient available stock for {line.product.name}.", 409)
        rows.append(StockReservation(company_id=order.company_id, order_line=line, product=line.product,
            location=location, request_id=request_id, quantity=quantity, actor_email=user.email))
    StockReservation.objects.bulk_create(rows)
    record_activity(user, order.company_id, "orders", order, f"Reserved stock for {order.number}")
    return rows, True


def release_reservations(order, user, data):
    """Release an entire retry-safe reservation request before it is picked."""
    request_id = request_uuid(data, required=True)
    rows = list(StockReservation.objects.select_for_update().filter(company_id=order.company_id,
        request_id=request_id, order_line__order=order))
    if not rows:
        raise APIError("Reservation request not found for this sales order.", 404)
    if any(row.operation_id for row in rows):
        raise APIError("Reservations assigned to a delivery cannot be released.", 409)
    changed = False
    for row in rows:
        if row.state == "active":
            row.state = "released"; row.save(update_fields=["state", "updated_at"]); changed = True
    if changed:
        record_activity(user, order.company_id, "orders", order, f"Released reservation for {order.number}")
    return rows, changed


def operation_data(operation):
    return {"id": operation.pk, "number": operation.number, "order_id": operation.order_id,
            "source_location_id": operation.source_location_id, "status": operation.status,
            "backorder_of_id": operation.backorder_of_id, "request_id": operation.request_id,
            "lines": [{"id": line.pk, "order_line_id": line.order_line_id, "product_id": line.product_id,
                       "description": line.description, "planned_quantity": line.planned_quantity,
                       "done_quantity": line.done_quantity} for line in operation.lines.all()]}


def create_delivery(order, user, data, *, backorder_of=None, quantities=None):
    if order.kind != "sale" or order.status != "confirmed":
        raise APIError("Deliveries require a confirmed sales order.", 409)
    request_id = request_uuid(data, required=True)
    existing = StockOperation.objects.filter(request_id=request_id).prefetch_related("lines").first()
    if existing:
        if existing.company_id != order.company_id or existing.order_id != order.pk:
            raise APIError("This delivery request was already used with different details.", 409)
        return existing, False
    location, _ = ensure_defaults(order.company_id)
    reservations = list(StockReservation.objects.select_for_update().filter(order_line__order=order,
        state="active", operation__isnull=True).select_related("order_line", "product"))
    by_line = {}
    for row in reservations:
        by_line[row.order_line_id] = by_line.get(row.order_line_id, ZERO) + row.quantity
    if quantities is None:
        quantities = by_line
    if not quantities:
        raise APIError("Reserve goods before creating a delivery.", 409)
    lines = {line.pk: line for line in order.lines.filter(product_kind="goods").select_related("product")}
    if set(quantities) - set(lines) or any(value <= 0 or value > by_line.get(key, ZERO) for key, value in quantities.items()):
        raise APIError("A delivery can contain only currently reserved goods quantities.", 409)
    operation = StockOperation.objects.create(company_id=order.company_id, order=order,
        number=next_number(order.company_id, "PICK"), request_id=request_id, source_location=location,
        backorder_of=backorder_of, actor_email=user.email)
    StockOperationLine.objects.bulk_create([StockOperationLine(operation=operation, order_line=lines[line_id],
        product=lines[line_id].product, description=lines[line_id].description, planned_quantity=quantity)
        for line_id, quantity in quantities.items()])
    # A reservation row is deliberately claimed by one operation, so it cannot be picked twice.
    for row in reservations:
        if row.order_line_id in quantities:
            row.operation = operation; row.save(update_fields=["operation", "updated_at"])
    operation = StockOperation.objects.prefetch_related("lines").get(pk=operation.pk)
    record_activity(user, order.company_id, "orders", order, f"Created delivery {operation.number}: {order.number}")
    return operation, True


def validate_delivery(operation, user, data):
    if operation.status == "done":
        return operation, False, None
    if operation.status != "draft":
        raise APIError("Only draft deliveries can be validated.", 409)
    raw = data.get("lines")
    if not isinstance(raw, list) or not raw:
        raise APIError("Supply completed quantities for this delivery.")
    done = {}
    for entry in raw:
        if not isinstance(entry, dict) or set(entry) != {"line_id", "quantity"}:
            raise APIError("Each delivery line needs only line_id and quantity.")
        line_id = positive_id(entry["line_id"])
        if line_id in done: raise APIError("Each delivery line may appear only once.")
        done[line_id] = decimal_value(entry["quantity"], "Delivered quantity", places=3, minimum=ZERO, maximum=MAX_QUANTITY)
    lines = {line.pk: line for line in operation.lines.select_related("product", "order_line")}
    if set(done) != set(lines) or any(quantity > lines[key].planned_quantity for key, quantity in done.items()):
        raise APIError("Delivered quantities must match this delivery's planned lines.", 409)
    for line_id, quantity in done.items():
        if quantity:
            line = lines[line_id]
            StockMovement.objects.create(company_id=operation.company_id, product=line.product, order=operation.order,
                order_line=line.order_line, operation=operation, quantity=-quantity,
                reason=f"Delivery {operation.number}: {operation.order.number}", actor_email=user.email)
        lines[line_id].done_quantity = quantity
    StockOperationLine.objects.bulk_update(list(lines.values()), ["done_quantity"])
    operation.status = "done"; operation.save(update_fields=["status", "updated_at"])
    remainder = {line.order_line_id: line.planned_quantity - done[line.pk] for line in lines.values() if line.planned_quantity > done[line.pk]}
    backorder = None
    if remainder:
        # Reuse the claimed reservations; no extra capacity is created.
        StockReservation.objects.filter(operation=operation, state="active").update(operation=None)
        backorder, _ = create_delivery(operation.order, user, {"request_id": str(uuid4())}, backorder_of=operation, quantities=remainder)
    else:
        StockReservation.objects.filter(operation=operation, state="active").update(state="consumed")
    goods = operation.order.lines.filter(product_kind="goods")
    delivered = {row["order_line_id"]: -row["value"] for row in StockMovement.objects.filter(order=operation.order,
        quantity__lt=0, operation__isnull=False).values("order_line_id").annotate(value=Sum("quantity"))}
    if all(delivered.get(line.pk, ZERO) >= line.quantity for line in goods):
        operation.order.fulfilled_at = timezone.now(); operation.order.version += 1
        operation.order.save(update_fields=["fulfilled_at", "version", "updated_at"])
    record_activity(user, operation.company_id, "orders", operation.order, f"Validated delivery {operation.number}")
    return StockOperation.objects.prefetch_related("lines").get(pk=operation.pk), True, backorder


def request_uuid(data, *, required=False):
    value = data.get("request_id")
    if value is None and not required:
        return uuid4()
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        raise APIError("Send a UUID request_id and retain it when retrying this operation.")
    try:
        return UUID(value)
    except ValueError:
        raise APIError("request_id must be a UUID.") from None


def purchase_lines(order):
    return order.lines.filter(product_kind="goods").select_related("product").annotate(received_quantity=Coalesce(
        Sum("movements__quantity"), Value(ZERO), output_field=DecimalField(max_digits=20, decimal_places=3),
    ))


def update_receipt_state(order):
    complete = all(line.received_quantity == line.quantity for line in purchase_lines(order))
    order.fulfilled_at = timezone.now() if complete else None
    order.version += 1
    order.save(update_fields=["fulfilled_at", "version", "updated_at"])


def receive_purchase(order, user, data, *, require_version=True):
    if order.kind != "purchase":
        raise APIError("Receipts require a purchase order.")
    request_id = request_uuid(data, required=require_version)
    notes = text_field(data, "notes", maximum=300, required=False)
    raw = data.get("lines")
    quantities = None
    if raw is not None:
        if not isinstance(raw, list) or not 1 <= len(raw) <= 100:
            raise APIError("Choose 1 to 100 purchase lines to receive.")
        quantities = {}
        for entry in raw:
            if not isinstance(entry, dict) or set(entry) != {"line_id", "quantity"}:
                raise APIError("Each receipt line needs only line_id and quantity.")
            line_id = positive_id(entry["line_id"])
            if line_id in quantities:
                raise APIError("Each purchase line may appear only once in a receipt.")
            quantities[line_id] = decimal_value(entry["quantity"], "Receipt quantity", places=3,
                minimum=Decimal("0.001"), maximum=MAX_QUANTITY)
    canonical = {"order": order.pk, "notes": notes, "lines": None if quantities is None else
                 sorted((key, str(value)) for key, value in quantities.items())}
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
    existing = PurchaseReceipt.objects.filter(request_id=request_id).first()
    if existing:
        if (existing.company_id, existing.order_id, existing.payload_digest) != (order.company_id, order.pk, digest):
            raise APIError("This receipt request was already used with different details.", 409)
        return existing, False
    if require_version:
        check_version(order, data)
    if order.status != "confirmed":
        raise APIError("Confirm the purchase order before receiving products.", 409)
    if order.fulfilled_at:
        raise APIError("This purchase order is already fully received.", 409)
    lines = {line.pk: line for line in purchase_lines(order)}
    if quantities is None:
        quantities = {line.pk: line.quantity - line.received_quantity for line in lines.values()
                      if line.received_quantity < line.quantity}
    if set(quantities) - set(lines):
        raise APIError("Choose goods lines belonging to this purchase order.")
    for line_id, quantity in quantities.items():
        line = lines[line_id]
        if quantity > line.quantity - line.received_quantity:
            raise APIError(f"The receipt exceeds the remaining quantity for {line.description}.", 409)
    if not quantities and lines:
        raise APIError("There are no remaining quantities to receive.", 409)
    receipt = PurchaseReceipt.objects.create(company_id=order.company_id, order=order,
        number=next_number(order.company_id, "REC"), request_id=request_id, payload_digest=digest,
        notes=notes, actor_email=user.email)
    for line_id, quantity in quantities.items():
        line = lines[line_id]
        StockMovement.objects.create(company_id=order.company_id, product=line.product, order=order,
            order_line=line, receipt=receipt, quantity=quantity, reason=f"Receipt {receipt.number}: {order.number}",
            actor_email=user.email)
    update_receipt_state(order)
    record_activity(user, order.company_id, "orders", order, f"Receipt {receipt.number}: {order.number}")
    return receipt, True


def adjustment(user, company_id, data):
    product_id = positive_id(data.get("product_id"))
    quantity = decimal_value(data.get("quantity"), "Stock change", places=3,
        minimum=-MAX_QUANTITY, maximum=MAX_QUANTITY)
    if quantity == 0:
        raise APIError("The stock change must be nonzero.")
    reason = text_field(data, "reason", maximum=300)
    request_id = request_uuid(data)
    existing = StockMovement.objects.filter(request_id=request_id).first()
    if existing:
        if (existing.company_id, existing.product_id, existing.quantity, existing.reason,
                existing.order_id, existing.return_of_id, existing.reversal_of_id) != (
                company_id, product_id, quantity, reason, None, None, None):
            raise APIError("This stock request was already used with different details.", 409)
        return existing, False
    product = scoped(Product, company_id, product_id)
    if product.kind != "goods" or not product.is_active:
        raise APIError("Stock adjustments require an active goods product.")
    reserved = StockReservation.objects.filter(company_id=company_id, product=product, state="active").aggregate(value=Sum("quantity"))["value"] or ZERO
    if stock_for(product) + quantity < reserved:
        raise APIError("This change would consume stock already reserved for delivery.", 409)
    movement = StockMovement.objects.create(company_id=company_id, product=product, quantity=quantity,
        reason=reason, actor_email=user.email, request_id=request_id)
    record_activity(user, company_id, "products", product, f"Stock {quantity:+}: {product.name} — {reason}")
    return movement, True


def correct_movement(user, company_id, source, data, *, supplier_return):
    request_id = request_uuid(data, required=True)
    reason = text_field(data, "reason", maximum=300)
    if supplier_return:
        if (source.quantity <= 0 or not source.order_id or source.order.kind != "purchase" or
                source.return_of_id or source.reversal_of_id or not source.order_line_id):
            raise APIError("Choose an original purchase receipt movement for a supplier return.")
        amount = decimal_value(data.get("quantity"), "Return quantity", places=3,
            minimum=Decimal("0.001"), maximum=MAX_QUANTITY)
        quantity = -amount
    else:
        if source.order_id or source.return_of_id or source.reversal_of_id or source.quantity == 0:
            raise APIError("Only an original manual adjustment can be reversed here.")
        quantity = -source.quantity
    existing = StockMovement.objects.filter(request_id=request_id).first()
    expected_return, expected_reversal = (source.pk, None) if supplier_return else (None, source.pk)
    if existing:
        if (existing.company_id, existing.quantity, existing.reason, existing.return_of_id, existing.reversal_of_id) != (
                company_id, quantity, reason, expected_return, expected_reversal):
            raise APIError("This stock request was already used with different details.", 409)
        return existing, False
    if supplier_return:
        returned = source.returns.aggregate(value=Sum("quantity"))["value"] or ZERO
        if -quantity > source.quantity + returned:
            raise APIError("The return exceeds this receipt's unreturned quantity.", 409)
    elif StockMovement.objects.filter(reversal_of=source).exists():
        raise APIError("This adjustment has already been reversed.", 409)
    if stock_for(source.product) + quantity < 0:
        raise APIError("There is not enough stock to record this correction.", 409)
    movement = StockMovement.objects.create(company_id=company_id, product=source.product,
        order=source.order if supplier_return else None,
        order_line=source.order_line if supplier_return else None,
        receipt=source.receipt if supplier_return else None, quantity=quantity, reason=reason,
        actor_email=user.email, request_id=request_id,
        return_of_id=expected_return, reversal_of_id=expected_reversal)
    if supplier_return:
        update_receipt_state(source.order)
    label = "Supplier return" if supplier_return else "Adjustment reversal"
    record_activity(user, company_id, "products", source.product, f"{label} {quantity:+}: {source.product.name} — {reason}")
    return movement, True
