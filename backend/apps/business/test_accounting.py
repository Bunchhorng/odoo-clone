from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.test import TestCase
from django.utils import timezone

from apps.companies.models import Company, CompanyMembership
from apps.core.api import APIError
from .accounting import create_entry, report
from .models import AccountingSettings, Activity, Contact, Invoice, JournalEntry, JournalLine, LedgerAccount, Order, Payment, Product


class AccountingWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("ledger-owner@example.test")
        cls.member = get_user_model().objects.create_user("ledger-member@example.test")
        cls.admin = get_user_model().objects.create_user("ledger-admin@example.test")
        cls.company = Company.objects.create(name="Ledger", slug="ledger")
        cls.other = Company.objects.create(name="Private ledger", slug="private-ledger")
        for user, role in ((cls.owner, "owner"), (cls.member, "member"), (cls.admin, "admin")):
            CompanyMembership.objects.create(company=cls.company, user=user, role=role)
        cls.contact = Contact.objects.create(company=cls.company, name="Partner", is_customer=True, is_supplier=True)
        cls.product = Product.objects.create(company=cls.company, name="Service", sku="LEDGER", kind="service", sale_price="100", cost_price="40")

    def setUp(self):
        self.client.force_login(self.owner)
        self.base = f"/api/v1/companies/{self.company.pk}/erp/"
        self.today = timezone.localdate()
        self.yesterday = self.today - timedelta(days=1)

    def call(self, method, endpoint, body=None, status=200):
        result = getattr(self.client, method)(self.base + endpoint, body, content_type="application/json")
        self.assertEqual(result.status_code, status, result.content)
        return result.json()

    def invoice(self, kind="sale", tax="7", amount=None, posting_date=None):
        line = {"product_id": self.product.pk, "quantity": "1", "tax_rate": tax}
        if amount is not None:
            line["unit_price"] = amount
        order = self.call("post", "orders/", {"kind": kind, "contact_id": self.contact.pk, "lines": [line]}, 201)
        order = self.call("post", f"orders/{order['id']}/actions/", {"action": "confirm", "expected_version": order["version"]})
        invoice = self.call("post", f"orders/{order['id']}/actions/", {"action": "invoice", "expected_version": order["version"]})
        if posting_date:
            invoice = self.call("patch", f"invoices/{invoice['id']}/", {"date": posting_date.isoformat(), "expected_version": invoice["version"]})
        return invoice

    def transition(self, invoice, action, status=200, **fields):
        return self.call("post", f"invoices/{invoice['id']}/actions/", {"action": action, "expected_version": invoice["version"], **fields}, status)

    def pay(self, invoice, amount, method="bank", **fields):
        return self.call("post", f"invoices/{invoice['id']}/payments/", {"amount": amount, "method": method, **fields})

    def balances(self, entry):
        return {line.account.code: (line.debit, line.credit) for line in entry.lines.select_related("account")}

    def assert_balanced(self):
        for entry in JournalEntry.objects.all():
            sums = entry.lines.aggregate(debit=Sum("debit"), credit=Sum("credit"))
            self.assertEqual(sums["debit"], sums["credit"])

    def test_drafts_and_order_confirmation_have_no_financial_posting(self):
        invoice = self.invoice()
        self.assertFalse(JournalEntry.objects.exists())
        self.transition(invoice, "cancel")
        self.assertFalse(JournalEntry.objects.exists())
        self.assertFalse(LedgerAccount.objects.exists())

    def test_customer_invoice_and_partial_bank_cash_payments_balance_and_reconcile(self):
        invoice = self.transition(self.invoice(), "issue")
        entry = JournalEntry.objects.get(kind="invoice")
        self.assertEqual(self.balances(entry), {"1100": (Decimal("107"), 0), "4000": (0, Decimal("100")), "2100": (0, Decimal("7"))})
        self.pay(invoice, "20")
        paid = self.pay(invoice, "87", "cash")
        self.assertEqual(paid["status"], "paid")
        self.assertEqual(paid["journal_entry_count"], 3)
        summary = report(self.company.pk, self.today, self.today)
        rows = {row["code"]: row for row in summary["accounts"]}
        self.assertEqual(rows["1100"]["balance"], 0)
        self.assertEqual(rows["1000"]["balance"], 20)
        self.assertEqual(rows["1010"]["balance"], 87)
        self.assertEqual(summary["profit"], 100)
        self.assertEqual(summary["balance_check"], 0)
        self.assert_balanced()

    def test_vendor_bill_expenses_input_tax_and_outbound_payment(self):
        invoice = self.transition(self.invoice("purchase"), "issue")
        self.assertEqual(self.balances(JournalEntry.objects.get()), {"5000": (Decimal("40"), 0), "1200": (Decimal("2.8"), 0), "2000": (0, Decimal("42.8"))})
        self.pay(invoice, "12.80")
        summary = report(self.company.pk, self.today, self.today)
        rows = {row["code"]: row for row in summary["accounts"]}
        self.assertEqual(rows["2000"]["balance"], -30)
        self.assertEqual(rows["1000"]["balance"], Decimal("-12.80"))
        self.assertEqual(summary["expenses"], 40)
        self.assertEqual(summary["balance_check"], 0)
        order = self.call("get", f"orders/{invoice['order_id']}/")
        self.assertEqual(order["invoice_summary"]["balance"], "30.00")
        self.assertEqual(order["invoice_summary"]["journal_entry_count"], 2)
        self.assert_balanced()

    def test_issue_and_payment_retries_do_not_duplicate_entries_activity_or_numbers(self):
        draft = self.invoice()
        issued = self.transition(draft, "issue")
        self.transition(draft, "issue")
        token = str(uuid4())
        self.pay(issued, "107", request_id=token)
        self.pay(issued, "107", request_id=token)
        self.assertEqual(JournalEntry.objects.count(), 2)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Activity.objects.filter(summary__startswith="Issue:").count(), 1)
        self.assertEqual(Activity.objects.filter(summary__startswith="Payment ").count(), 1)
        self.assertEqual(set(JournalEntry.objects.values_list("number", flat=True)), {"JE00001", "JE00002"})

    def test_cancellation_reverses_without_mutating_posted_lines_and_reissue_uses_new_entry(self):
        invoice = self.transition(self.invoice(), "issue")
        original = JournalEntry.objects.get()
        before = list(original.lines.values("id", "account_id", "debit", "credit"))
        cancelled = self.transition(invoice, "cancel")
        self.transition(invoice, "cancel")
        reversal = JournalEntry.objects.get(reversal_of=original)
        self.assertEqual(reversal.date, self.today)
        self.assertEqual(list(original.lines.values("id", "account_id", "debit", "credit")), before)
        self.assertEqual(report(self.company.pk, self.today, self.today)["profit"], 0)
        restored = self.transition(cancelled, "restore")
        self.transition(restored, "issue")
        self.assertEqual(JournalEntry.objects.count(), 3)
        self.assertEqual(report(self.company.pk, self.today, self.today)["profit"], 100)
        self.assert_balanced()

    def test_paid_invoice_cancellation_is_rejected_without_any_reversal(self):
        invoice = self.transition(self.invoice(), "issue")
        paid = self.pay(invoice, "1")
        self.transition(paid, "cancel", 409)
        self.assertEqual(JournalEntry.objects.count(), 2)
        self.assertFalse(JournalEntry.objects.filter(kind="reversal").exists())

    def test_zero_value_document_has_traceable_zero_entry(self):
        invoice = self.transition(self.invoice(amount="0"), "issue")
        self.assertEqual(invoice["status"], "paid")
        self.assertEqual(JournalEntry.objects.count(), 1)
        self.assertFalse(JournalLine.objects.exists())
        self.assertEqual(report(self.company.pk, self.today, self.today)["balance_check"], 0)

    def test_closed_dates_reject_issue_and_payment_atomically_but_allow_open_reversal(self):
        invoice = self.transition(self.invoice(posting_date=self.yesterday), "issue")
        draft = self.invoice(posting_date=self.yesterday)
        self.call("patch", "accounting/settings/", {"locked_through": self.yesterday.isoformat(), "expected_version": 1})
        self.transition(draft, "issue", 409)
        self.call("post", f"invoices/{invoice['id']}/payments/", {"amount": "1", "date": self.yesterday.isoformat()}, 409)
        self.assertFalse(Payment.objects.exists())
        self.assertEqual(Invoice.objects.get(pk=invoice["id"]).version, invoice["version"])
        self.transition(invoice, "cancel", 409, reversal_date=self.yesterday.isoformat())
        self.transition(invoice, "cancel", reversal_date=self.today.isoformat())
        self.assertEqual(JournalEntry.objects.count(), 2)
        self.assertEqual(Invoice.objects.get(pk=draft["id"]).status, "draft")

    def test_lock_dates_require_owner_versions_and_only_move_forward(self):
        self.client.force_login(self.admin)
        self.call("patch", "accounting/settings/", {"locked_through": self.yesterday.isoformat(), "expected_version": 1}, 403)
        self.client.force_login(self.owner)
        self.call("patch", "accounting/settings/", {"locked_through": self.yesterday.isoformat(), "expected_version": 1})
        self.call("patch", "accounting/settings/", {"locked_through": self.today.isoformat(), "expected_version": 1}, 409)
        for value in (None, self.yesterday.isoformat(), (self.today + timedelta(days=1)).isoformat()):
            self.call("patch", "accounting/settings/", {"locked_through": value, "expected_version": 2}, 400 if value is None or value > self.today.isoformat() else 409)
        self.assertEqual(AccountingSettings.objects.get().locked_through, self.yesterday)

    def test_historical_import_is_explicit_idempotent_and_blocks_closing_unposted_dates(self):
        invoice = self.invoice(posting_date=self.yesterday)
        Invoice.objects.filter(pk=invoice["id"]).update(status="issued")
        payment = Payment.objects.create(company=self.company, invoice_id=invoice["id"], request_id=uuid4(), amount="5", date=self.yesterday)
        settings = self.call("get", "accounting/settings/")
        self.assertEqual((settings["unposted_invoices"], settings["unposted_payments"]), (1, 1))
        self.assertFalse(JournalEntry.objects.exists())
        self.call("patch", "accounting/settings/", {"locked_through": self.yesterday.isoformat(), "expected_version": 1}, 409)
        self.assertFalse(AccountingSettings.objects.exists())
        self.assertEqual(self.call("post", "accounting/sync/", {})["created"], 2)
        self.assertEqual(self.call("post", "accounting/sync/", {})["created"], 0)
        self.assertEqual(JournalEntry.objects.get(payment=payment).date, self.yesterday)
        self.assertEqual(Activity.objects.filter(summary__startswith="Imported 2 historical").count(), 1)
        self.assertEqual(self.call("get", "accounting/settings/")["unposted_payments"], 0)
        self.call("patch", "accounting/settings/", {"locked_through": self.yesterday.isoformat(), "expected_version": 1})

    def test_period_opening_balances_and_reversals_preserve_prior_period_reports(self):
        invoice = self.transition(self.invoice(posting_date=self.yesterday), "issue")
        self.transition(invoice, "cancel", reversal_date=self.today.isoformat())
        yesterday = report(self.company.pk, self.yesterday, self.yesterday)
        today = report(self.company.pk, self.today, self.today)
        self.assertEqual(yesterday["profit"], 100)
        self.assertEqual(today["profit"], -100)
        self.assertEqual(today["accumulated_earnings"], 0)
        receivable = next(row for row in today["accounts"] if row["code"] == "1100")
        self.assertEqual(receivable["opening"], 107)
        self.assertEqual(receivable["balance"], 0)
        self.assertEqual(today["closing_debit"], today["closing_credit"])

    def test_company_and_member_scope_and_immutable_entry_endpoints(self):
        invoice = self.transition(self.invoice(), "issue")
        self.client.force_login(self.member)
        entries = self.call("get", f"accounting/entries/?invoice_id={invoice['id']}")
        self.assertEqual(entries["count"], 1)
        self.call("post", "accounting/sync/", {}, 403)
        self.call("patch", "accounting/settings/", {}, 403)
        self.call("post", "accounting/entries/", {}, 405)
        entry = JournalEntry.objects.get()
        self.assertEqual(self.client.patch(self.base + f"accounting/entries/{entry.pk}/", {}, content_type="application/json").status_code, 404)
        private = self.client.get(f"/api/v1/companies/{self.other.pk}/erp/accounting/reports/")
        self.assertEqual(private.status_code, 404)
        CompanyMembership.objects.create(company=self.other, user=self.member)
        old_base, self.base = self.base, f"/api/v1/companies/{self.other.pk}/erp/"
        self.call("get", f"accounting/entries/?invoice_id={invoice['id']}", status=404)
        self.call("get", f"accounting/entries/?order_id={invoice['order_id']}", status=404)
        self.assertEqual(self.call("get", "accounting/reports/")["revenue"], "0")
        self.base = old_base

    def test_entry_filters_dates_accounts_journals_sources_and_bounded_ids(self):
        sale = self.transition(self.invoice(), "issue")
        self.transition(self.invoice("purchase"), "issue")
        self.pay(sale, "1")
        for query in ("account=4000", "journal=bank", f"q={sale['order_number']}&journal=sales"):
            self.assertEqual(self.call("get", f"accounting/entries/?{query}")["count"], 1)
        self.assertEqual(self.call("get", f"accounting/entries/?invoice_id={sale['id']}")["count"], 2)
        for query in ("account=invalid", "journal=invalid", "date_from=bad", "date_from=2099-01-01&date_to=2000-01-01", "invoice_id=NaN", "order_id=" + "9" * 30):
            self.call("get", f"accounting/entries/?{query}", status=400)
        self.assert_balanced()

    def test_unbalanced_internal_posting_rolls_back_and_admin_cannot_mutate_ledger(self):
        invoice = Invoice.objects.get(pk=self.invoice()["id"])
        with self.assertRaises(APIError), transaction.atomic():
            create_entry(invoice, source_key="invalid", kind="invoice", journal="sales", posting_date=self.today,
                description="Invalid", lines=[("1100", Decimal("1"), Decimal("0"))])
        self.assertFalse(JournalEntry.objects.exists())
        for model in (JournalEntry, JournalLine, LedgerAccount, AccountingSettings):
            handler = admin.site._registry[model]
            self.assertFalse(handler.has_add_permission(None))
            self.assertFalse(handler.has_change_permission(None))
            self.assertFalse(handler.has_delete_permission(None))
