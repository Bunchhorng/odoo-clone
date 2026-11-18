"""Company-scoped business rules. Call write_access inside an atomic transaction."""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import UUID, uuid4

from django.db.models import Sum
from django.utils import timezone

from apps.companies.access import membership_for
from apps.companies.models import Company
from apps.core.api import APIError
from .models import (
    Activity, Contact, DocumentSequence, Invoice, Opportunity, Order, OrderLine,
    Payment, Product, StockMovement, WorkspaceSettings,
)

CENT = Decimal("0.01")
ZERO = Decimal("0")


def write_access(user, company_id):
    membership_for(user, company_id)
    if Company.objects.select_for_update().filter(pk=company_id).first() is None:
        raise APIError("Company not found.", 404)
    actor = membership_for(user, company_id)
    if actor.role not in ("owner", "admin"):
        raise APIError("An owner or administrator is required to change business records.", 403)
    return actor


def record_activity(user, company_id, resource, obj, summary):
    Activity.objects.create(company_id=company_id, actor_email=user.email,
                            resource=resource, record_id=obj.pk, summary=summary[:400])


def scoped(model, company_id, record_id):
    item = model.objects.filter(company_id=company_id, pk=positive_id(record_id)).first()
    if item is None:
        raise APIError("Record not found in this company.", 404)
    return item


def positive_id(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise APIError("Choose a valid record.")
    representation = str(value)
    if not 1 <= len(representation) <= 19 or not representation.isascii() or not representation.isdecimal():
        raise APIError("Choose a valid record.")
    number = int(representation)
    if not 0 < number <= 9223372036854775807:
        raise APIError("Choose a valid record.")
    return number


def check_version(item, data):
    expected = data.get("expected_version")
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
        raise APIError("Send the document's expected_version from its latest response.")
    if expected != item.version:
        raise APIError("This document changed in another session. Reload it and review the latest values before continuing.", 409)


def decimal_value(value, label, *, places=2, minimum=ZERO, maximum=Decimal("9999999999.99")):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)) or len(str(value)) > 64:
        raise APIError(f"{label} must be a valid number.")
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < minimum or number > maximum:
            raise InvalidOperation
        rounded = number.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
        if rounded != number:
            raise APIError(f"{label} may have at most {places} decimal places.")
        return rounded
    except (InvalidOperation, ValueError):
        raise APIError(f"{label} must be between {minimum} and {maximum}.") from None


def date_value(value, label, *, optional=False):
    if optional and value in (None, ""):
        return None
    if not isinstance(value, str) or len(value) != 10:
        raise APIError(f"{label} must be a date in YYYY-MM-DD format.")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise APIError(f"{label} must be a valid date.") from None


def next_number(company_id, prefix):
    # Company row is already locked, including on the first sequence allocation.
    sequence, _ = DocumentSequence.objects.get_or_create(company_id=company_id, prefix=prefix)
    sequence.value += 1
    sequence.save(update_fields=["value"])
    return f"{prefix}{sequence.value:05d}"


def currency_for(company_id):
    settings = WorkspaceSettings.objects.filter(company_id=company_id).first()
    return settings.currency if settings else "USD"


def stock_for(product):
    return product.movements.aggregate(value=Sum("quantity"))["value"] or ZERO


def paid_for(invoice):
    if hasattr(invoice, "paid_amount"):
        return invoice.paid_amount or ZERO
    return invoice.payments.aggregate(value=Sum("amount"))["value"] or ZERO


def build_lines(company_id, raw_lines, kind, order=None):
    if not isinstance(raw_lines, list) or not 1 <= len(raw_lines) <= 100:
        raise APIError("An order needs 1 to 100 product lines.")
    lines = []
    existing = {line.pk: line for line in order.lines.all()} if order else {}
    used = set()
    for raw in raw_lines:
        if not isinstance(raw, dict) or set(raw) - {"id", "product_id", "description", "quantity", "unit_price", "tax_rate"}:
            raise APIError("An order line contains unsupported fields.")
        line_id = positive_id(raw["id"]) if "id" in raw else None
        if line_id is not None and (line_id not in existing or line_id in used):
            raise APIError("Choose each existing line from this order only once.")
        used.add(line_id)
        product = scoped(Product, company_id, raw.get("product_id"))
        retained = line_id is not None and existing[line_id].product_id == product.pk
        if not product.is_active and not retained:
            raise APIError("An archived product cannot be added to an order.")
        quantity = decimal_value(raw.get("quantity"), "Quantity", places=3, minimum=Decimal("0.001"), maximum=Decimal("999999999.999"))
        price = decimal_value(raw.get("unit_price", product.sale_price if kind == "sale" else product.cost_price), "Unit price")
        tax_rate = decimal_value(raw.get("tax_rate", 0), "Tax rate", maximum=Decimal("100"))
        description = raw.get("description", product.name)
        if not isinstance(description, str) or not description.strip() or len(description) > 300:
            raise APIError("Line descriptions must contain 1 to 300 characters.")
        subtotal = (quantity * price).quantize(CENT, rounding=ROUND_HALF_UP)
        tax = (subtotal * tax_rate / 100).quantize(CENT, rounding=ROUND_HALF_UP)
        total = subtotal + tax
        if total > Decimal("99999999999999.99"):
            raise APIError("The line total is too large.")
        lines.append(OrderLine(id=line_id, product=product, product_kind=product.kind, description=description.strip(),
                               quantity=quantity, unit_price=price, tax_rate=tax_rate,
                               subtotal=subtotal, tax_total=tax, total=total))
    if sum(line.total for line in lines) > Decimal("99999999999999.99"):
        raise APIError("The order total is too large.")
    return lines


def save_order(company_id, data, order=None):
    creating = order is None
    if creating:
        kind = data.get("kind")
        if kind not in ("sale", "purchase"):
            raise APIError("Choose sale or purchase as the order kind.")
        order = Order(company_id=company_id, kind=kind, currency=currency_for(company_id))
    elif order.status != "draft":
        raise APIError("Only draft quotations or RFQs can be edited.", 409)
    elif "kind" in data and data["kind"] != order.kind:
        raise APIError("An order's kind cannot be changed.")
    if "opportunity_id" in data:
        opportunity_id = positive_id(data["opportunity_id"]) if data["opportunity_id"] is not None else None
        if not creating and opportunity_id != order.opportunity_id:
            raise APIError("An order's opportunity cannot be changed.")
        if opportunity_id is not None:
            opportunity = scoped(Opportunity, company_id, opportunity_id)
            if order.kind != "sale":
                raise APIError("Only sales quotations can be linked to an opportunity.")
            if creating and not opportunity.is_active:
                raise APIError("Restore the opportunity before creating a quotation.")
            order.opportunity = opportunity
    if "contact_id" in data or creating:
        contact = scoped(Contact, company_id, data.get("contact_id"))
        changed_contact = creating or contact.pk != order.contact_id
        if changed_contact and not contact.is_active:
            raise APIError("Choose an active contact.")
        if changed_contact and order.kind == "sale" and not contact.is_customer:
            raise APIError("The contact must be a customer.")
        if changed_contact and order.kind == "purchase" and not contact.is_supplier:
            raise APIError("The contact must be a supplier.")
        order.contact = contact
        if changed_contact:
            order.contact_name, order.contact_email, order.contact_address = contact.name, contact.email, contact.address
    if "date" in data:
        order.date = date_value(data["date"], "Order date")
    if "notes" in data:
        if not isinstance(data["notes"], str) or len(data["notes"]) > 10000:
            raise APIError("Notes must be text with at most 10000 characters.")
        order.notes = data["notes"]
    lines = build_lines(company_id, data["lines"], order.kind, None if creating else order) if "lines" in data else None
    if creating and lines is None:
        raise APIError("Add at least one product line.")
    if lines is not None:
        order.subtotal = sum(line.subtotal for line in lines)
        order.tax_total = sum(line.tax_total for line in lines)
        order.total = sum(line.total for line in lines)
    if creating:
        order.number = next_number(company_id, "SO" if order.kind == "sale" else "PO")
    else:
        order.version += 1
    order.full_clean()
    order.save()
    if lines is not None:
        retained_ids = [line.pk for line in lines if line.pk is not None]
        order.lines.exclude(pk__in=retained_ids).delete()
        for line in lines:
            line.order = order
        OrderLine.objects.bulk_update([line for line in lines if line.pk is not None],
            ["product", "product_kind", "description", "quantity", "unit_price", "tax_rate", "subtotal", "tax_total", "total"])
        OrderLine.objects.bulk_create([line for line in lines if line.pk is None])
    return order


def fulfill_order(order, user):
    if order.status != "confirmed":
        raise APIError("Confirm the order before delivering or receiving it.", 409)
    if order.fulfilled_at:
        return False
    if order.kind == "purchase":
        from .inventory import receive_purchase
        _, created = receive_purchase(order, user, {}, require_version=False)
        return created
    lines = list(order.lines.filter(product_kind="goods").select_related("product"))
    required = {}
    for line in lines:
        required[line.product_id] = required.get(line.product_id, ZERO) + line.quantity
    if order.kind == "sale":
        for product_id, quantity in required.items():
            product = next(line.product for line in lines if line.product_id == product_id)
            if stock_for(product) < quantity:
                raise APIError(f"Insufficient stock for {product.name}. Receive or adjust stock first.", 409)
    for line in lines:
        StockMovement.objects.create(company_id=order.company_id, product=line.product, order=order, order_line=line,
                                     quantity=-line.quantity if order.kind == "sale" else line.quantity,
                                     reason=f"{'Delivery' if order.kind == 'sale' else 'Receipt'} {order.number}",
                                     actor_email=user.email)
    order.fulfilled_at = timezone.now()
    order.version += 1
    order.save(update_fields=["fulfilled_at", "version", "updated_at"])
    return True


def invoice_order(order):
    if order.status != "confirmed":
        raise APIError("Only confirmed orders can be invoiced.", 409)
    existing = Invoice.objects.filter(order=order).first()
    if existing:
        return existing
    invoice = Invoice(company_id=order.company_id, order=order,
                      number=next_number(order.company_id, "INV" if order.kind == "sale" else "BILL"),
                      kind="customer" if order.kind == "sale" else "vendor",
                      contact=order.contact, contact_name=order.contact_name, contact_email=order.contact_email,
                      contact_address=order.contact_address, currency=order.currency,
                      subtotal=order.subtotal, tax_total=order.tax_total, total=order.total, notes=order.notes)
    invoice.full_clean()
    invoice.save()
    return invoice


def register_payment(invoice, data, *, actor_email=""):
    try:
        request_id = UUID(str(data.get("request_id", uuid4())))
    except (ValueError, AttributeError):
        raise APIError("Payment request_id must be a UUID.") from None
    amount = decimal_value(data.get("amount"), "Payment amount", minimum=CENT, maximum=Decimal("99999999999999.99"))
    payment_date = date_value(data.get("date", timezone.localdate().isoformat()), "Payment date")
    method, reference = data.get("method", "bank"), data.get("reference", "")
    if method not in ("bank", "cash") or not isinstance(reference, str) or len(reference) > 200:
        raise APIError("Choose a valid payment method and a reference up to 200 characters.")
    existing = Payment.objects.filter(request_id=request_id).first()
    if existing:
        if (existing.invoice_id, existing.company_id, existing.amount, existing.date, existing.method, existing.reference) != (
            invoice.pk, invoice.company_id, amount, payment_date, method, reference,
        ):
            raise APIError("This payment request was already used with different details.", 409)
        return existing, False
    if invoice.status != "issued":
        raise APIError("Payments can only be recorded on an issued, unpaid invoice or bill.", 409)
    if amount > invoice.total - paid_for(invoice):
        raise APIError("The payment exceeds the remaining balance.", 409)
    if payment_date < invoice.date:
        raise APIError("The payment date cannot precede the invoice date.")
    payment = Payment(company_id=invoice.company_id, invoice=invoice, request_id=request_id,
                      amount=amount, date=payment_date, method=method, reference=reference)
    payment.full_clean()
    payment.save()
    if invoice.total - paid_for(invoice) == ZERO:
        invoice.status = "paid"
    invoice.version += 1
    invoice.save(update_fields=["status", "version", "updated_at"])
    from .accounting import post_payment
    post_payment(payment, actor_email)
    return payment, True
