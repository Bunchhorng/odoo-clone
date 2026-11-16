from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connections
from django.db.models import Sum
from django.test import Client, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from apps.companies.models import Company, CompanyMembership
from .models import Activity, CatalogImport, Contact, Employee, HelpdeskTicket, Invoice, JournalEntry, Order, Payment, Product, Project, PurchaseReceipt, StockMovement, Task, TimesheetEntry
from .services import invoice_order, save_order


class BusinessConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("parallel@example.com")
        self.company = Company.objects.create(name="Parallel", slug="parallel")
        CompanyMembership.objects.create(company=self.company, user=self.user, role="owner")
        self.contact = Contact.objects.create(company=self.company, name="Customer")
        self.product = Product.objects.create(company=self.company, name="Product", sku="PARALLEL", sale_price="20")
        self.service_product = Product.objects.create(company=self.company, name="Service", sku="PARALLEL-SERVICE", kind="service", sale_price="20")
        self.clients = [Client(), Client()]
        for client in self.clients:
            client.force_login(self.user)
        self.base = f"/api/v1/companies/{self.company.pk}/erp/"

    def order(self, quantity, *, service=False):
        order = save_order(self.company.pk, {"kind": "sale", "contact_id": self.contact.pk,
                           "lines": [{"product_id": self.service_product.pk if service else self.product.pk, "quantity": quantity}]})
        order.status = "confirmed"
        order.save(update_fields=["status"])
        return order

    def run_parallel(self, endpoints, bodies, method="post"):
        barrier = Barrier(2)

        def run(index):
            try:
                barrier.wait(timeout=10)
                response = getattr(self.clients[index], method)(self.base + endpoints[index], bodies[index], content_type="application/json")
                return response.status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return sorted(pool.map(run, (0, 1)))

    @skipUnlessDBFeature("has_select_for_update")
    def test_simultaneous_deliveries_do_not_oversell(self):
        StockMovement.objects.create(company=self.company, product=self.product, quantity=10, reason="Opening", actor_email=self.user.email)
        orders = [self.order("8"), self.order("8")]
        statuses = self.run_parallel([f"orders/{order.pk}/actions/" for order in orders], [{"action": "fulfill", "expected_version": order.version} for order in orders])
        self.assertEqual(statuses, [200, 409])
        self.assertEqual(StockMovement.objects.aggregate(value=Sum("quantity"))["value"], 2)
        self.assertEqual(Order.objects.filter(fulfilled_at__isnull=False).count(), 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_payments_cannot_exceed_balance(self):
        invoice = invoice_order(self.order("2", service=True))
        invoice.status = "issued"
        invoice.save(update_fields=["status"])
        endpoint = f"invoices/{invoice.pk}/payments/"
        statuses = self.run_parallel([endpoint] * 2, [{"amount": "30", "request_id": str(uuid4())} for _ in range(2)])
        self.assertEqual(statuses, [200, 409])
        self.assertEqual(Payment.objects.filter(invoice=invoice).count(), 1)
        self.assertEqual(Payment.objects.get(invoice=invoice).amount, 30)
        self.assertEqual(Invoice.objects.get(pk=invoice.pk).status, "issued")

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_retry_records_one_payment(self):
        invoice = invoice_order(self.order("2", service=True))
        invoice.status = "issued"
        invoice.save(update_fields=["status"])
        endpoint = f"invoices/{invoice.pk}/payments/"
        payload = {"amount": "40", "request_id": str(uuid4())}
        statuses = self.run_parallel([endpoint] * 2, [payload, payload])
        self.assertEqual(statuses, [200, 200])
        self.assertEqual(Payment.objects.filter(invoice=invoice).count(), 1)
        self.assertEqual(Invoice.objects.get(pk=invoice.pk).status, "paid")
        self.assertEqual(Activity.objects.filter(resource="invoices", record_id=invoice.pk, summary__startswith="Payment ").count(), 1)
        self.assertEqual(JournalEntry.objects.filter(invoice=invoice, kind="invoice").count(), 1)
        self.assertEqual(JournalEntry.objects.filter(invoice=invoice, kind="payment").count(), 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_csv_retry_creates_one_batch(self):
        text = "name\nConcurrent import contact\n"
        response = self.clients[0].post(self.base + "contacts/import/preview/", {"csv": text}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        body = {"csv": text, "token": response.json()["token"]}
        self.assertEqual(self.run_parallel(["contacts/import/"] * 2, [body, body]), [200, 201])
        self.assertEqual(Contact.objects.filter(name="Concurrent import contact").count(), 1)
        self.assertEqual(CatalogImport.objects.count(), 1)
        self.assertEqual(Activity.objects.filter(summary="Imported Concurrent import contact").count(), 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_draft_edits_reject_one_stale_version(self):
        order = save_order(self.company.pk, {"kind": "sale", "contact_id": self.contact.pk,
            "lines": [{"product_id": self.product.pk, "quantity": "1"}]})
        endpoint = f"orders/{order.pk}/"
        bodies = [{"notes": notes, "expected_version": order.version} for notes in ("First editor", "Second editor")]
        self.assertEqual(self.run_parallel([endpoint] * 2, bodies, "patch"), [200, 409])
        order.refresh_from_db()
        self.assertEqual(order.version, 2)
        self.assertIn(order.notes, ("First editor", "Second editor"))

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_invoice_creation_logs_one_completion(self):
        order = self.order("1", service=True)
        body = {"action": "invoice", "expected_version": order.version}
        self.assertEqual(self.run_parallel([f"orders/{order.pk}/actions/"] * 2, [body, body]), [200, 200])
        self.assertEqual(Invoice.objects.filter(order=order).count(), 1)
        self.assertEqual(Activity.objects.filter(resource="invoices", summary__startswith="Prepared ").count(), 1)

    def purchase_order(self):
        self.contact.is_supplier = True
        self.contact.save()
        order = save_order(self.company.pk, {"kind": "purchase", "contact_id": self.contact.pk,
            "lines": [{"product_id": self.product.pk, "quantity": "5"}]})
        order.status = "confirmed"
        order.save(update_fields=["status"])
        return order

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_partial_receipt_retry_has_one_completion(self):
        order = self.purchase_order()
        body = {"expected_version": order.version, "request_id": str(uuid4()),
                "lines": [{"line_id": order.lines.get().pk, "quantity": "2"}]}
        self.assertEqual(self.run_parallel([f"orders/{order.pk}/receipts/"] * 2, [body, body]), [200, 201])
        self.assertEqual(PurchaseReceipt.objects.count(), 1)
        self.assertEqual(StockMovement.objects.get().quantity, 2)
        self.assertEqual(Activity.objects.filter(summary__startswith="Receipt ").count(), 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_receipts_reject_stale_quantities(self):
        order = self.purchase_order()
        bodies = [{"expected_version": order.version, "request_id": str(uuid4()),
                   "lines": [{"line_id": order.lines.get().pk, "quantity": "4"}]} for _ in range(2)]
        self.assertEqual(self.run_parallel([f"orders/{order.pk}/receipts/"] * 2, bodies), [201, 409])
        self.assertEqual(StockMovement.objects.get().quantity, 4)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_supplier_returns_cannot_exceed_receipt(self):
        order = self.purchase_order()
        response = self.clients[0].post(self.base + f"orders/{order.pk}/receipts/", {
            "expected_version": order.version, "request_id": str(uuid4()),
        }, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        source = StockMovement.objects.get(order=order)
        bodies = [{"quantity": "4", "reason": "Return", "request_id": str(uuid4())} for _ in range(2)]
        self.assertEqual(self.run_parallel([f"stock/{source.pk}/return/"] * 2, bodies), [201, 409])
        self.assertEqual(StockMovement.objects.filter(return_of=source).count(), 1)
        self.assertEqual(StockMovement.objects.aggregate(total=Sum("quantity"))["total"], 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_adjustment_retry_records_one_entry(self):
        body = {"product_id": self.product.pk, "quantity": "5", "reason": "Count", "request_id": str(uuid4())}
        self.assertEqual(self.run_parallel(["stock/"] * 2, [body, body]), [200, 201])
        self.assertEqual(StockMovement.objects.count(), 1)
        self.assertEqual(Activity.objects.count(), 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_reversals_only_reverse_an_adjustment_once(self):
        source = StockMovement.objects.create(company=self.company, product=self.product, quantity="5",
            reason="Count", actor_email=self.user.email)
        bodies = [{"reason": "Incorrect count", "request_id": str(uuid4())} for _ in range(2)]
        self.assertEqual(self.run_parallel([f"stock/{source.pk}/reverse/"] * 2, bodies), [201, 409])
        self.assertEqual(StockMovement.objects.filter(reversal_of=source).count(), 1)
        self.assertEqual(StockMovement.objects.aggregate(total=Sum("quantity"))["total"], 0)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_invoice_issue_creates_one_balanced_posting(self):
        invoice = invoice_order(self.order("2", service=True))
        body = {"action": "issue", "expected_version": invoice.version}
        self.assertEqual(self.run_parallel([f"invoices/{invoice.pk}/actions/"] * 2, [body, body]), [200, 200])
        self.assertEqual(JournalEntry.objects.filter(invoice=invoice).count(), 1)
        entry = JournalEntry.objects.get(invoice=invoice)
        totals = entry.lines.aggregate(debit=Sum("debit"), credit=Sum("credit"))
        self.assertEqual(totals["debit"], 40)
        self.assertEqual(totals["debit"], totals["credit"])
        self.assertEqual(Activity.objects.filter(summary__startswith="Issue:").count(), 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_historical_import_posts_each_source_once(self):
        invoice = invoice_order(self.order("2", service=True))
        invoice.status = "issued"
        invoice.save(update_fields=["status"])
        self.assertEqual(self.run_parallel(["accounting/sync/"] * 2, [{}, {}]), [200, 200])
        self.assertEqual(JournalEntry.objects.filter(invoice=invoice).count(), 1)
        self.assertEqual(Activity.objects.filter(summary="Imported 1 historical accounting postings").count(), 1)

    def time_payload(self, minutes=60):
        employee = Employee.objects.create(company=self.company, name="Specialist", employee_code="SPECIALIST", user=self.user)
        project = Project.objects.create(company=self.company, name="Customer setup")
        return {"employee_id": employee.pk, "project_id": project.pk, "date": timezone.localdate().isoformat(),
                "minutes": minutes, "description": "Setup work", "request_id": str(uuid4())}

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_time_entries_cannot_exceed_employee_daily_limit(self):
        body = self.time_payload(800)
        self.assertEqual(self.run_parallel(["timesheets/"] * 2, [body, {**body, "request_id": str(uuid4())}]), [201, 409])
        self.assertEqual(TimesheetEntry.objects.count(), 1)
        self.assertEqual(TimesheetEntry.objects.get().minutes, 800)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_time_submission_retry_creates_one_draft(self):
        body = self.time_payload()
        self.assertEqual(self.run_parallel(["timesheets/"] * 2, [body, body]), [200, 201])
        self.assertEqual(TimesheetEntry.objects.count(), 1)
        self.assertEqual(Activity.objects.filter(resource="timesheets").count(), 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_ticket_task_conversion_creates_one_task(self):
        project = Project.objects.create(company=self.company, name="Support")
        result = self.clients[0].post(self.base + "helpdesk/", {"title": "Network setup", "project_id": project.pk,
            "request_id": str(uuid4())}, content_type="application/json")
        self.assertEqual(result.status_code, 201)
        ticket = result.json()
        body = {"action": "create_task", "expected_version": ticket["version"]}
        self.assertEqual(self.run_parallel([f"helpdesk/{ticket['id']}/actions/"] * 2, [body, body]), [200, 200])
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Activity.objects.filter(summary__startswith="Create task:").count(), 1)
        self.assertEqual(HelpdeskTicket.objects.get().task_id, Task.objects.get().pk)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_time_review_rejects_one_stale_decision(self):
        response = self.clients[0].post(self.base + "timesheets/", self.time_payload(), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        entry = response.json()
        endpoint = f"timesheets/{entry['id']}/actions/"
        submitted = self.clients[0].post(self.base + endpoint, {"action": "submit", "expected_version": entry["version"]}, content_type="application/json").json()
        bodies = [{"action": "approve", "expected_version": submitted["version"]},
                  {"action": "reject", "expected_version": submitted["version"], "reason": "Clarify work"}]
        self.assertEqual(self.run_parallel([endpoint] * 2, bodies), [200, 409])
        self.assertIn(TimesheetEntry.objects.get().status, ("draft", "approved"))
