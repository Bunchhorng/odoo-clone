"""Document-derived accrual ledger. All writers hold the company lock in an atomic transaction.

This is a generic, fixed chart. Purchases are expensed on bill issue; stock has no
cost layers and never posts valuation entries. Manual bank/cash records represent
settled payments, not bank statement reconciliation.
"""
from decimal import Decimal

from django.db.models import Q, Sum

from apps.core.api import APIError
from .models import AccountingSettings, Invoice, JournalEntry, JournalLine, LedgerAccount, Payment
from .services import ZERO, currency_for, next_number

CHART = (
    ("1000", "Bank", "asset"), ("1010", "Cash", "asset"),
    ("1100", "Accounts receivable", "asset"), ("1200", "Input tax", "asset"),
    ("2000", "Accounts payable", "liability"), ("2100", "Output tax", "liability"),
    ("4000", "Sales revenue", "income"), ("5000", "Purchases expense", "expense"),
)


def assert_open(company_id, posting_date):
    settings = AccountingSettings.objects.filter(company_id=company_id).first()
    if settings and settings.locked_through and posting_date <= settings.locked_through:
        raise APIError(f"Accounting is locked through {settings.locked_through}. Choose an open posting date.", 409)


def active_invoice_entry(invoice):
    return invoice.journal_entries.filter(kind="invoice", reversal__isnull=True).first()


def create_entry(invoice, *, source_key, kind, journal, posting_date, description, lines,
                 actor_email="", payment=None, reversal_of=None):
    # Source keys and the company lock make sequential and concurrent retries safe.
    existing = JournalEntry.objects.filter(company_id=invoice.company_id, source_key=source_key).first()
    if existing:
        return existing
    assert_open(invoice.company_id, posting_date)
    if invoice.currency != currency_for(invoice.company_id):
        raise APIError("Document and company currencies must agree before posting.", 409)
    if (any(code not in {row[0] for row in CHART} or debit < 0 or credit < 0 or (debit and credit)
            or debit != debit.quantize(Decimal(".01")) or credit != credit.quantize(Decimal(".01"))
            for code, debit, credit in lines)
            or sum(row[1] for row in lines) != sum(row[2] for row in lines)):
        raise APIError("A journal entry must contain valid, balanced debit and credit amounts.", 409)
    accounts = {item.code: item for item in LedgerAccount.objects.filter(company_id=invoice.company_id)}
    missing = [LedgerAccount(company_id=invoice.company_id, code=code, name=name, kind=account_kind)
               for code, name, account_kind in CHART if code not in accounts]
    if missing:
        LedgerAccount.objects.bulk_create(missing)
        accounts = {item.code: item for item in LedgerAccount.objects.filter(company_id=invoice.company_id)}
    entry = JournalEntry.objects.create(company_id=invoice.company_id, number=next_number(invoice.company_id, "JE"),
        source_key=source_key, kind=kind, journal=journal, date=posting_date, currency=invoice.currency,
        description=description, invoice=invoice, payment=payment, reversal_of=reversal_of, actor_email=actor_email)
    JournalLine.objects.bulk_create([JournalLine(entry=entry, account=accounts[code], debit=debit, credit=credit)
                                   for code, debit, credit in lines if debit or credit])
    # A zero-value invoice has a numbered entry and no monetary lines.
    return entry


def post_invoice(invoice, actor_email=""):
    existing = active_invoice_entry(invoice)
    if existing:
        return existing
    if invoice.subtotal < 0 or invoice.tax_total < 0 or invoice.total != invoice.subtotal + invoice.tax_total:
        raise APIError("Invoice totals must reconcile before posting.", 409)
    customer = invoice.kind == "customer"
    lines = ([("1100", invoice.total, ZERO), ("4000", ZERO, invoice.subtotal), ("2100", ZERO, invoice.tax_total)]
             if customer else [("5000", invoice.subtotal, ZERO), ("1200", invoice.tax_total, ZERO), ("2000", ZERO, invoice.total)])
    revision = invoice.journal_entries.filter(kind="invoice").count() + 1
    return create_entry(invoice, source_key=f"invoice:{invoice.pk}:{revision}", kind="invoice",
        journal="sales" if customer else "purchases", posting_date=invoice.date,
        description=f"{'Invoice' if customer else 'Vendor bill'} {invoice.number}", lines=lines, actor_email=actor_email)


def post_payment(payment, actor_email=""):
    existing = JournalEntry.objects.filter(payment=payment).first()
    if existing:
        return existing
    invoice = payment.invoice
    post_invoice(invoice, actor_email)
    cash_account = "1000" if payment.method == "bank" else "1010"
    lines = ([(cash_account, payment.amount, ZERO), ("1100", ZERO, payment.amount)] if invoice.kind == "customer"
             else [("2000", payment.amount, ZERO), (cash_account, ZERO, payment.amount)])
    return create_entry(invoice, source_key=f"payment:{payment.pk}", kind="payment", journal=payment.method,
        posting_date=payment.date, description=f"Payment for {invoice.number}", lines=lines, payment=payment, actor_email=actor_email)


def reverse_invoice(invoice, posting_date, actor_email=""):
    original = active_invoice_entry(invoice)
    if original is None and invoice.status in ("issued", "paid"):
        original = post_invoice(invoice, actor_email)
    if original is None:
        return None  # Cancelling a draft has no financial effect.
    if posting_date < original.date:
        raise APIError("The reversal date cannot precede the original posting date.")
    return create_entry(invoice, source_key=f"reversal:{original.pk}", kind="reversal", journal=original.journal,
        posting_date=posting_date, description=f"Cancellation of {invoice.number} ({original.number})",
        lines=[(line.account.code, line.credit, line.debit) for line in original.lines.select_related("account")],
        reversal_of=original, actor_email=actor_email)


def missing_postings(company_id):
    invoices = Invoice.objects.filter(company_id=company_id, status__in=("issued", "paid")).exclude(
        pk__in=JournalEntry.objects.filter(company_id=company_id, kind="invoice", reversal__isnull=True).values("invoice_id"))
    payments = Payment.objects.filter(company_id=company_id, journal_entry__isnull=True)
    return invoices, payments


def synchronize(company_id, actor_email):
    invoices, payments = missing_postings(company_id)
    count = 0
    for invoice in invoices.order_by("date", "id"):
        post_invoice(invoice, actor_email)
        count += 1
    for payment in payments.select_related("invoice").order_by("date", "id"):
        post_payment(payment, actor_email)
        count += 1
    return count


def report(company_id, date_from, date_to):
    lines = JournalLine.objects.filter(entry__company_id=company_id, entry__date__lte=date_to)
    grouped = {row["account__code"]: row for row in lines.values("account__code").annotate(
        opening_debit=Sum("debit", filter=Q(entry__date__lt=date_from)),
        opening_credit=Sum("credit", filter=Q(entry__date__lt=date_from)),
        debit=Sum("debit", filter=Q(entry__date__gte=date_from)),
        credit=Sum("credit", filter=Q(entry__date__gte=date_from)))}
    rows = []
    for code, name, kind in CHART:
        current = grouped.get(code, {})
        opening_balance = (current.get("opening_debit") or ZERO) - (current.get("opening_credit") or ZERO)
        debit, credit = current.get("debit") or ZERO, current.get("credit") or ZERO
        balance = opening_balance + debit - credit
        rows.append({"code": code, "name": name, "kind": kind, "opening": opening_balance, "debit": debit,
                     "credit": credit, "balance": balance, "closing_debit": max(balance, ZERO), "closing_credit": max(-balance, ZERO)})
    revenue = sum((r["credit"] - r["debit"] for r in rows if r["kind"] == "income"), ZERO)
    expenses = sum((r["debit"] - r["credit"] for r in rows if r["kind"] == "expense"), ZERO)
    assets = sum((r["balance"] for r in rows if r["kind"] == "asset"), ZERO)
    liabilities = -sum((r["balance"] for r in rows if r["kind"] == "liability"), ZERO)
    earnings = -sum((r["balance"] for r in rows if r["kind"] in ("income", "expense")), ZERO)
    return {"date_from": date_from, "date_to": date_to, "currency": currency_for(company_id), "accounts": rows,
            "debit": sum((r["debit"] for r in rows), ZERO), "credit": sum((r["credit"] for r in rows), ZERO),
            "closing_debit": sum((r["closing_debit"] for r in rows), ZERO), "closing_credit": sum((r["closing_credit"] for r in rows), ZERO),
            "revenue": revenue, "expenses": expenses, "profit": revenue - expenses,
            "assets": assets, "liabilities": liabilities, "accumulated_earnings": earnings,
            "balance_check": assets - liabilities - earnings}
