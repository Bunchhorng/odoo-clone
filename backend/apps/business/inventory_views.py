from datetime import datetime, time

from django.db import transaction
from django.db.models import Prefetch, Q, Sum
from django.http import JsonResponse
from django.utils import timezone

from apps.companies.access import membership_for
from apps.core.api import APIError, api, json_body
from .inventory import adjustment, correct_movement, receive_purchase, reserve_sale
from .models import Order, Product, PurchaseReceipt, StockLocation, StockMovement
from .services import ZERO, date_value, scoped, stock_for, write_access
from .views import order_data, page


def movement_queryset(company_id):
    return StockMovement.objects.filter(company_id=company_id).select_related(
        "product", "order", "receipt", "reversal", "source_location", "destination_location",
    ).annotate(returned_quantity=Sum("returns__quantity"))


def movement_data(item):
    kind = ("return" if item.return_of_id else "reversal" if item.reversal_of_id else
            "receipt" if item.order_id and item.order.kind == "purchase" else "delivery" if item.order_id else "adjustment")
    reversal = getattr(item, "reversal", None)
    returnable = item.quantity + (item.returned_quantity or ZERO) if kind == "receipt" and item.order_line_id else ZERO
    return {"id": item.pk, "product_id": item.product_id, "product_name": item.product.name,
            "sku": item.product.sku, "unit": item.product.unit, "quantity": item.quantity, "reason": item.reason,
            "order_id": item.order_id, "order_kind": item.order.kind if item.order_id else None,
            "order_number": item.order.number if item.order_id else "Adjustment", "order_line_id": item.order_line_id,
            "receipt_id": item.receipt_id, "receipt_number": item.receipt.number if item.receipt_id else "",
            "receipt_notes": item.receipt.notes if item.receipt_id else "",
            "request_id": item.request_id, "kind": kind, "return_of_id": item.return_of_id,
            "source_location_id": item.source_location_id, "source_location_code": item.source_location.code,
            "destination_location_id": item.destination_location_id, "destination_location_code": item.destination_location.code,
            "location_inferred": item.location_inferred,
            "reversal_of_id": item.reversal_of_id, "reversed_by_id": reversal.pk if reversal else None,
            "returnable_quantity": returnable, "can_reverse": kind == "adjustment" and not reversal and item.quantity != 0,
            "created_at": item.created_at, "actor_email": item.actor_email}


def receipt_data(receipt):
    movements = (receipt.received_movements if hasattr(receipt, "received_movements") else
        movement_queryset(receipt.company_id).filter(receipt=receipt, quantity__gt=0, return_of__isnull=True))
    return {"id": receipt.pk, "number": receipt.number, "order_id": receipt.order_id, "request_id": receipt.request_id,
            "notes": receipt.notes, "actor_email": receipt.actor_email, "created_at": receipt.created_at,
            "movements": [movement_data(item) for item in movements]}


@api(["GET", "POST"])
def receipts(request, company_id, record_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        order = scoped(Order, company_id, record_id)
        if order.kind != "purchase":
            raise APIError("Receipts require a purchase order.")
        queryset = PurchaseReceipt.objects.filter(company_id=company_id, order=order).prefetch_related(Prefetch(
            "movements", queryset=movement_queryset(company_id).filter(quantity__gt=0, return_of__isnull=True), to_attr="received_movements",
        ))
        return page(request, queryset, receipt_data)
    with transaction.atomic():
        write_access(request.user, company_id)
        order = scoped(Order, company_id, record_id)
        receipt, created = receive_purchase(order, request.user, json_body(request, {"lines", "notes", "request_id", "expected_version"}))
        return JsonResponse({"receipt": receipt_data(receipt), "order": order_data(order, True), "replayed": not created}, status=201 if created else 200)


@api(["POST"])
def reservations(request, company_id, record_id):
    with transaction.atomic():
        write_access(request.user, company_id)
        order = scoped(Order, company_id, record_id)
        rows, created = reserve_sale(order, request.user, json_body(request, {"lines", "request_id"}))
        return JsonResponse({"reservations": [{"id": item.pk, "order_line_id": item.order_line_id,
            "product_id": item.product_id, "location_id": item.location_id, "quantity": item.quantity,
            "state": item.state} for item in rows], "replayed": not created}, status=201 if created else 200)


@api(["GET", "POST"])
def stock(request, company_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        queryset = movement_queryset(company_id)
        if request.GET.get("product_id"):
            queryset = queryset.filter(product=scoped(Product, company_id, request.GET["product_id"]))
        if request.GET.get("order_id"):
            queryset = queryset.filter(order=scoped(Order, company_id, request.GET["order_id"]))
        if request.GET.get("location_id"):
            location = scoped(StockLocation, company_id, request.GET["location_id"])
            queryset = queryset.filter(Q(source_location=location) | Q(destination_location=location))
        query = request.GET.get("q", "").strip()[:200]
        if query:
            queryset = queryset.filter(Q(product__name__icontains=query) | Q(product__sku__icontains=query) |
                Q(reason__icontains=query) | Q(order__number__icontains=query) | Q(receipt__number__icontains=query) | Q(receipt__notes__icontains=query))
        kind = request.GET.get("kind", "all")
        kinds = {"adjustment": Q(order__isnull=True, return_of__isnull=True, reversal_of__isnull=True),
                 "receipt": Q(order__kind="purchase", quantity__gt=0, return_of__isnull=True),
                 "delivery": Q(order__kind="sale", return_of__isnull=True),
                 "return": Q(return_of__isnull=False), "reversal": Q(reversal_of__isnull=False)}
        if kind != "all":
            if kind not in kinds:
                raise APIError("Choose all, adjustment, receipt, delivery, return, or reversal.")
            queryset = queryset.filter(kinds[kind])
        first = date_value(request.GET["date_from"], "Start date") if request.GET.get("date_from") else None
        last = date_value(request.GET["date_to"], "End date") if request.GET.get("date_to") else None
        if first and last and first > last:
            raise APIError("The end date cannot precede the start date.")
        if first:
            queryset = queryset.filter(created_at__gte=timezone.make_aware(datetime.combine(first, time.min)))
        if last:
            queryset = queryset.filter(created_at__lte=timezone.make_aware(datetime.combine(last, time.max)))
        return page(request, queryset, movement_data)
    with transaction.atomic():
        write_access(request.user, company_id)
        movement, created = adjustment(request.user, company_id, json_body(request, {"product_id", "quantity", "reason", "request_id"}))
        item = movement_queryset(company_id).get(pk=movement.pk)
        return JsonResponse({**movement_data(item), "stock_quantity": stock_for(item.product), "replayed": not created}, status=201 if created else 200)


def correction(request, company_id, record_id, *, supplier_return):
    with transaction.atomic():
        write_access(request.user, company_id)
        source = scoped(StockMovement, company_id, record_id)
        allowed = {"quantity", "reason", "request_id"} if supplier_return else {"reason", "request_id"}
        movement, created = correct_movement(request.user, company_id, source, json_body(request, allowed), supplier_return=supplier_return)
        item = movement_queryset(company_id).get(pk=movement.pk)
        return JsonResponse({**movement_data(item), "stock_quantity": stock_for(item.product), "replayed": not created}, status=201 if created else 200)


@api(["POST"])
def supplier_return(request, company_id, record_id):
    return correction(request, company_id, record_id, supplier_return=True)


@api(["POST"])
def reverse_adjustment(request, company_id, record_id):
    return correction(request, company_id, record_id, supplier_return=False)
