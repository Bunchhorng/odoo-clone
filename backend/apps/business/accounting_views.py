from datetime import date

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from apps.companies.access import membership_for
from apps.core.api import APIError, api, json_body
from .accounting import CHART, missing_postings, report, synchronize
from .models import AccountingSettings, Invoice, JournalEntry, Order
from .services import check_version, currency_for, date_value, record_activity, scoped, write_access
from .views import page


def entry_data(entry):
    return {"id": entry.pk, "number": entry.number, "kind": entry.kind, "journal": entry.journal,
        "date": entry.date, "currency": entry.currency, "description": entry.description,
        "invoice_id": entry.invoice_id, "invoice_number": entry.invoice.number,
        "order_id": entry.invoice.order_id, "order_number": entry.invoice.order.number,
        "order_kind": entry.invoice.order.kind, "contact_name": entry.invoice.contact_name,
        "payment_id": entry.payment_id, "reversal_of_id": entry.reversal_of_id,
        "reversal_id": getattr(getattr(entry, "reversal", None), "pk", None),
        "actor_email": entry.actor_email, "created_at": entry.created_at,
        "lines": [{"account_code": line.account.code, "account_name": line.account.name,
                   "debit": line.debit, "credit": line.credit} for line in entry.lines.all()]}


def dates(request):
    end = date_value(request.GET.get("date_to", timezone.localdate().isoformat()), "End date")
    start = date_value(request.GET.get("date_from", date(end.year, 1, 1).isoformat()), "Start date")
    if start > end:
        raise APIError("Start date cannot follow end date.")
    return start, end


def settings_data(company_id):
    item = AccountingSettings.objects.filter(company_id=company_id).first()
    invoices, payments = missing_postings(company_id)
    return {"locked_through": item.locked_through if item else None, "version": item.version if item else 1,
            "unposted_invoices": invoices.count(), "unposted_payments": payments.count(), "currency": currency_for(company_id),
            "accounts": [{"code": code, "name": name, "kind": kind} for code, name, kind in CHART]}


@api(["GET", "PATCH"])
def settings(request, company_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        return JsonResponse(settings_data(company_id))
    with transaction.atomic():
        actor = write_access(request.user, company_id)
        if actor.role != "owner":
            raise APIError("Only a company owner can close accounting dates.", 403)
        data = json_body(request, {"locked_through", "expected_version"})
        item, _ = AccountingSettings.objects.get_or_create(company_id=company_id)
        check_version(item, data)
        lock_date = date_value(data.get("locked_through"), "Lock date")
        if lock_date > timezone.localdate():
            raise APIError("The lock date cannot be in the future.")
        if item.locked_through and lock_date <= item.locked_through:
            raise APIError("The accounting lock can only move forward.", 409)
        invoices, payments = missing_postings(company_id)
        if invoices.filter(date__lte=lock_date).exists() or payments.filter(date__lte=lock_date).exists():
            raise APIError("Import the missing historical postings before closing these dates.", 409)
        item.locked_through = lock_date
        item.version += 1
        item.save(update_fields=["locked_through", "version"])
        record_activity(request.user, company_id, "accounting", item, f"Closed accounting through {lock_date}")
        return JsonResponse(settings_data(company_id))


@api(["POST"])
def sync(request, company_id):
    with transaction.atomic():
        write_access(request.user, company_id)
        json_body(request, set())
        count = synchronize(company_id, request.user.email)
        if count:
            item, _ = AccountingSettings.objects.get_or_create(company_id=company_id)
            record_activity(request.user, company_id, "accounting", item, f"Imported {count} historical accounting postings")
        return JsonResponse({**settings_data(company_id), "created": count})


@api(["GET"])
def entries(request, company_id):
    membership_for(request.user, company_id)
    queryset = JournalEntry.objects.filter(company_id=company_id).select_related("invoice__order", "reversal").prefetch_related("lines__account")
    start, end = dates(request)
    queryset = queryset.filter(date__range=(start, end))
    for field, model in (("invoice_id", Invoice), ("order_id", Order)):
        if request.GET.get(field):
            item = scoped(model, company_id, request.GET[field])
            queryset = queryset.filter(**({"invoice_id": item.pk} if field == "invoice_id" else {"invoice__order_id": item.pk}))
    account = request.GET.get("account", "")
    if account:
        if account not in {row[0] for row in CHART}:
            raise APIError("Choose an account from this company's chart.")
        queryset = queryset.filter(lines__account__company_id=company_id, lines__account__code=account).distinct()
    journal = request.GET.get("journal", "")
    if journal:
        if journal not in ("sales", "purchases", "bank", "cash"):
            raise APIError("Choose a valid journal.")
        queryset = queryset.filter(journal=journal)
    if request.GET.get("q"):
        search = request.GET["q"][:200]
        queryset = queryset.filter(Q(number__icontains=search) | Q(invoice__number__icontains=search) |
                                  Q(invoice__contact_name__icontains=search) | Q(invoice__order__number__icontains=search))
    return page(request, queryset.order_by("-date", "-id"), entry_data)


@api(["GET"])
def reports(request, company_id):
    membership_for(request.user, company_id)
    start, end = dates(request)
    metadata = settings_data(company_id)
    metadata.pop("accounts")
    return JsonResponse({**metadata, **report(company_id, start, end)})
