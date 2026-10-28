from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.utils import timezone

from apps.companies.access import membership_for
from apps.core.api import APIError, api, json_body, text_field
from .catalog import catalog_data, catalog_queryset, definition, filtered_catalog, save_catalog
from .models import Activity, Contact, Invoice, Opportunity, Order, Payment, Product, Project, StockMovement, Task, WorkspaceSettings
from .services import (
    currency_for, date_value, decimal_value, fulfill_order, invoice_order,
    paid_for, record_activity, register_payment, save_order, scoped, stock_for, write_access,
)


def page(request, queryset, serializer):
    try:
        page_number = int(request.GET.get("page", "1"))
        size = int(request.GET.get("page_size", "25"))
    except (ValueError, TypeError):
        raise APIError("Page and page_size must be whole numbers.") from None
    if not 1 <= page_number <= 1000000 or not 1 <= size <= 100:
        raise APIError("Use a positive page and a page_size from 1 to 100.")
    count = queryset.count()
    page_number = min(page_number, max(1, (count + size - 1) // size))
    start = (page_number - 1) * size
    return JsonResponse({"results": [serializer(item) for item in queryset[start:start + size]],
                         "count": count, "page": page_number, "page_size": size})


def order_data(item, detail=False):
    data = {key: getattr(item, key) for key in (
        "id", "kind", "number", "contact_id", "contact_name", "contact_email", "contact_address", "currency",
        "date", "status", "notes", "subtotal", "tax_total", "total", "fulfilled_at", "created_at", "updated_at",
    )}
    invoice = getattr(item, "invoice", None)
    data["invoice_id"] = invoice.pk if invoice else None
    if detail:
        data["lines"] = [line_data(line) for line in item.lines.all()]
    return data


def line_data(line):
    return {key: getattr(line, key) for key in ("id", "product_id", "description", "product_kind", "quantity", "unit_price", "tax_rate", "subtotal", "tax_total", "total")}


def invoice_data(item, detail=False):
    data = {key: getattr(item, key) for key in (
        "id", "kind", "number", "order_id", "contact_id", "contact_name", "contact_email", "contact_address", "currency",
        "date", "due_date", "status", "subtotal", "tax_total", "total", "notes", "created_at", "updated_at",
    )}
    data["order_number"] = item.order.number
    data["paid_amount"] = paid_for(item)
    data["balance"] = item.total - data["paid_amount"] if item.status != "cancelled" else Decimal("0")
    if detail:
        data["lines"] = [line_data(line) for line in item.order.lines.all()]
        data["payments"] = [{key: getattr(payment, key) for key in ("id", "amount", "date", "method", "reference", "request_id")} for payment in item.payments.all()]
    return data


@api(["GET", "POST"])
def catalog(request, company_id, resource):
    membership_for(request.user, company_id)
    _, allowed = definition(resource)
    if request.method == "GET":
        queryset = filtered_catalog(resource, company_id, request.GET)
        return page(request, queryset, lambda item: catalog_data(resource, item))
    with transaction.atomic():
        write_access(request.user, company_id)
        item = save_catalog(resource, company_id, json_body(request, allowed))
        record_activity(request.user, company_id, resource, item, f"Created {getattr(item, 'name', getattr(item, 'title', resource))}")
        return JsonResponse(catalog_data(resource, item), status=201)


@api(["GET", "PATCH"])
def catalog_item(request, company_id, resource, record_id):
    membership_for(request.user, company_id)
    model, allowed = definition(resource)
    if request.method == "GET":
        item = catalog_queryset(resource, company_id).filter(pk=record_id).first()
        if item is None:
            raise APIError("Record not found.", 404)
        return JsonResponse(catalog_data(resource, item))
    with transaction.atomic():
        write_access(request.user, company_id)
        item = save_catalog(resource, company_id, json_body(request, allowed), scoped(model, company_id, record_id))
        record_activity(request.user, company_id, resource, item, f"Updated {getattr(item, 'name', getattr(item, 'title', resource))}")
        return JsonResponse(catalog_data(resource, item))


@api(["GET", "POST"])
def orders(request, company_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        queryset = Order.objects.filter(company_id=company_id).select_related("invoice")
        if request.GET.get("kind"):
            queryset = queryset.filter(kind=request.GET["kind"])
        if request.GET.get("status"):
            queryset = queryset.filter(status=request.GET["status"])
        if request.GET.get("q"):
            queryset = queryset.filter(Q(number__icontains=request.GET["q"][:200]) | Q(contact_name__icontains=request.GET["q"][:200]))
        return page(request, queryset, order_data)
    with transaction.atomic():
        write_access(request.user, company_id)
        order = save_order(company_id, json_body(request, {"kind", "contact_id", "date", "notes", "lines"}))
        record_activity(request.user, company_id, "orders", order, f"Created {order.number}")
        return JsonResponse(order_data(order, True), status=201)


@api(["GET", "PATCH"])
def order_item(request, company_id, record_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        return JsonResponse(order_data(scoped(Order, company_id, record_id), True))
    with transaction.atomic():
        write_access(request.user, company_id)
        order = save_order(company_id, json_body(request, {"kind", "contact_id", "date", "notes", "lines"}), scoped(Order, company_id, record_id))
        record_activity(request.user, company_id, "orders", order, f"Updated {order.number}")
        return JsonResponse(order_data(order, True))


@api(["POST"])
def order_action(request, company_id, record_id):
    with transaction.atomic():
        write_access(request.user, company_id)
        order = scoped(Order, company_id, record_id)
        action = json_body(request, {"action"}).get("action")
        if action == "confirm":
            if order.status == "cancelled":
                raise APIError("A cancelled order cannot be confirmed.", 409)
            order.status = "confirmed"
            order.save(update_fields=["status", "updated_at"])
        elif action == "cancel":
            if order.fulfilled_at or Invoice.objects.filter(order=order).exists():
                raise APIError("An order with stock movements or an invoice cannot be cancelled.", 409)
            order.status = "cancelled"
            order.save(update_fields=["status", "updated_at"])
        elif action == "fulfill":
            fulfill_order(order, request.user)
        elif action == "invoice":
            invoice = invoice_order(order)
            record_activity(request.user, company_id, "invoices", invoice, f"Prepared {invoice.number} from {order.number}")
            return JsonResponse(invoice_data(invoice, True))
        else:
            raise APIError("Choose confirm, cancel, fulfill, or invoice.")
        record_activity(request.user, company_id, "orders", order, f"{action.capitalize()}: {order.number}")
        return JsonResponse(order_data(order, True))


@api(["GET"])
def invoices(request, company_id):
    membership_for(request.user, company_id)
    queryset = Invoice.objects.filter(company_id=company_id).select_related("order").annotate(paid_amount=Sum("payments__amount"))
    for field in ("kind", "status"):
        if request.GET.get(field):
            queryset = queryset.filter(**{field: request.GET[field]})
    if request.GET.get("q"):
        queryset = queryset.filter(Q(number__icontains=request.GET["q"][:200]) | Q(contact_name__icontains=request.GET["q"][:200]))
    return page(request, queryset, invoice_data)


@api(["GET", "PATCH"])
def invoice_item(request, company_id, record_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        return JsonResponse(invoice_data(scoped(Invoice, company_id, record_id), True))
    with transaction.atomic():
        write_access(request.user, company_id)
        invoice = scoped(Invoice, company_id, record_id)
        if invoice.status != "draft":
            raise APIError("Only draft invoices can be edited.", 409)
        data = json_body(request, {"date", "due_date", "notes"})
        if "date" in data:
            invoice.date = date_value(data["date"], "Invoice date")
        if "due_date" in data:
            invoice.due_date = date_value(data["due_date"], "Due date", optional=True)
        if "notes" in data:
            invoice.notes = text_field(data, "notes", maximum=10000, required=False)
        if invoice.due_date and invoice.due_date < invoice.date:
            raise APIError("The due date cannot precede the invoice date.")
        invoice.full_clean()
        invoice.save()
        record_activity(request.user, company_id, "invoices", invoice, f"Updated {invoice.number}")
        return JsonResponse(invoice_data(invoice, True))


@api(["POST"])
def invoice_action(request, company_id, record_id):
    with transaction.atomic():
        write_access(request.user, company_id)
        invoice = scoped(Invoice, company_id, record_id)
        action = json_body(request, {"action"}).get("action")
        if action == "issue":
            if invoice.status != "draft":
                raise APIError("Only a draft invoice or bill can be issued.", 409)
            invoice.status = "paid" if invoice.total == 0 else "issued"
        elif action == "cancel":
            if invoice.payments.exists() or invoice.status == "paid":
                raise APIError("An invoice with payments cannot be cancelled.", 409)
            invoice.status = "cancelled"
        else:
            raise APIError("Choose issue or cancel.")
        invoice.save(update_fields=["status", "updated_at"])
        record_activity(request.user, company_id, "invoices", invoice, f"{action.capitalize()}: {invoice.number}")
        return JsonResponse(invoice_data(invoice, True))


@api(["POST"])
def payments(request, company_id, record_id):
    with transaction.atomic():
        write_access(request.user, company_id)
        invoice = scoped(Invoice, company_id, record_id)
        payment, created = register_payment(invoice, json_body(request, {"amount", "date", "method", "reference", "request_id"}))
        if created:
            record_activity(request.user, company_id, "invoices", invoice, f"Payment {payment.amount} {invoice.currency}: {invoice.number}")
        return JsonResponse(invoice_data(invoice, True))


@api(["GET", "POST"])
def stock(request, company_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        queryset = StockMovement.objects.filter(company_id=company_id).select_related("product", "order")
        return page(request, queryset, lambda item: {
            "id": item.pk, "product_id": item.product_id, "product_name": item.product.name,
            "sku": item.product.sku, "quantity": item.quantity, "reason": item.reason,
            "order_number": item.order.number if item.order_id else "Adjustment", "created_at": item.created_at,
            "actor_email": item.actor_email,
        })
    with transaction.atomic():
        write_access(request.user, company_id)
        data = json_body(request, {"product_id", "quantity", "reason"})
        product = scoped(Product, company_id, data.get("product_id"))
        if product.kind != "goods" or not product.is_active:
            raise APIError("Stock adjustments require an active goods product.")
        quantity = decimal_value(data.get("quantity"), "Stock change", places=3,
                                 minimum=Decimal("-999999999.999"), maximum=Decimal("999999999.999"))
        if quantity == 0:
            raise APIError("The stock change must be nonzero.")
        if stock_for(product) + quantity < 0:
            raise APIError("This change would make stock negative.", 409)
        reason = text_field(data, "reason", maximum=300)
        movement = StockMovement.objects.create(company_id=company_id, product=product, quantity=quantity, reason=reason, actor_email=request.user.email)
        record_activity(request.user, company_id, "products", product, f"Stock {quantity:+}: {product.name} — {reason}")
        return JsonResponse({"id": movement.pk, "stock_quantity": stock_for(product)}, status=201)


@api(["GET", "PATCH"])
def workspace_settings(request, company_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        return JsonResponse({"currency": currency_for(company_id), "currency_locked": Order.objects.filter(company_id=company_id).exists()})
    with transaction.atomic():
        write_access(request.user, company_id)
        data = json_body(request, {"currency"})
        item, _ = WorkspaceSettings.objects.get_or_create(company_id=company_id)
        if Order.objects.filter(company_id=company_id).exists() and data.get("currency") != item.currency:
            raise APIError("Currency cannot change after the first order. Create a separate company for a different currency.", 409)
        item.currency = data.get("currency")
        item.full_clean()
        item.save()
        return JsonResponse({"currency": item.currency, "currency_locked": Order.objects.filter(company_id=company_id).exists()})


@api(["GET"])
def dashboard(request, company_id):
    membership_for(request.user, company_id)
    orders = Order.objects.filter(company_id=company_id)
    invoices = Invoice.objects.filter(company_id=company_id)
    opportunities = Opportunity.objects.filter(company_id=company_id, is_active=True)
    open_invoices = invoices.filter(status="issued").annotate(paid_amount=Sum("payments__amount"))
    receivable = sum((item.total - (item.paid_amount or 0) for item in open_invoices if item.kind == "customer"), Decimal("0"))
    payable = sum((item.total - (item.paid_amount or 0) for item in open_invoices if item.kind == "vendor"), Decimal("0"))
    sales = orders.filter(kind="sale", status="confirmed").aggregate(value=Sum("total"))["value"] or 0
    products = Product.objects.filter(company_id=company_id, kind="goods", is_active=True).annotate(stock_quantity=Sum("movements__quantity"))
    data = {
        "currency": currency_for(company_id),
        "contacts": Contact.objects.filter(company_id=company_id, is_active=True).count(),
        "products": Product.objects.filter(company_id=company_id, is_active=True).count(),
        "open_opportunities": opportunities.exclude(stage__in=["won", "lost"]).count(),
        "pipeline_value": opportunities.exclude(stage__in=["won", "lost"]).aggregate(value=Sum("expected_revenue"))["value"] or 0,
        "sales_total": sales, "quotations": orders.filter(kind="sale", status="draft").count(),
        "receivable": receivable, "payable": payable,
        "low_stock": sum(1 for product in products if (product.stock_quantity or 0) <= product.reorder_level),
        "open_tasks": Task.objects.filter(company_id=company_id, is_active=True).exclude(stage="done").count(),
        "overdue_tasks": Task.objects.filter(company_id=company_id, is_active=True, due_date__lt=timezone.localdate()).exclude(stage="done").count(),
        "pipeline": list(opportunities.values("stage").annotate(count=Count("id"), value=Sum("expected_revenue")).order_by("stage")),
        "recent_orders": [order_data(item) for item in orders.select_related("invoice")[:5]],
        "activities": [{"id": item.pk, "summary": item.summary, "actor_email": item.actor_email, "resource": item.resource, "record_id": item.record_id, "created_at": item.created_at} for item in Activity.objects.filter(company_id=company_id)[:12]],
    }
    return JsonResponse(data)
