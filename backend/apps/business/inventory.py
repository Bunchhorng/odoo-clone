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
from .models import Product, PurchaseReceipt, StockMovement, StockReservation
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
    if stock_for(product) + quantity < 0:
        raise APIError("This change would make stock negative.", 409)
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
