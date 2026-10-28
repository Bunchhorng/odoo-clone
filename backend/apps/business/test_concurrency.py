from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connections
from django.db.models import Sum
from django.test import Client, TransactionTestCase, skipUnlessDBFeature

from apps.companies.models import Company, CompanyMembership
from .models import Activity, CatalogImport, Contact, Invoice, Order, Payment, Product, StockMovement
from .services import invoice_order, save_order


class BusinessConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("parallel@example.com")
        self.company = Company.objects.create(name="Parallel", slug="parallel")
        CompanyMembership.objects.create(company=self.company, user=self.user, role="owner")
        self.contact = Contact.objects.create(company=self.company, name="Customer")
        self.product = Product.objects.create(company=self.company, name="Product", sku="PARALLEL", sale_price="20")
        self.clients = [Client(), Client()]
        for client in self.clients:
            client.force_login(self.user)
        self.base = f"/api/v1/companies/{self.company.pk}/erp/"

    def order(self, quantity):
        order = save_order(self.company.pk, {"kind": "sale", "contact_id": self.contact.pk,
                           "lines": [{"product_id": self.product.pk, "quantity": quantity}]})
        order.status = "confirmed"
        order.save(update_fields=["status"])
        return order

    def run_parallel(self, endpoints, bodies):
        barrier = Barrier(2)

        def run(index):
            try:
                barrier.wait(timeout=10)
                response = self.clients[index].post(self.base + endpoints[index], bodies[index], content_type="application/json")
                return response.status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return sorted(pool.map(run, (0, 1)))

    @skipUnlessDBFeature("has_select_for_update")
    def test_simultaneous_deliveries_do_not_oversell(self):
        StockMovement.objects.create(company=self.company, product=self.product, quantity=10, reason="Opening", actor_email=self.user.email)
        orders = [self.order("8"), self.order("8")]
        statuses = self.run_parallel([f"orders/{order.pk}/actions/" for order in orders], [{"action": "fulfill"}] * 2)
        self.assertEqual(statuses, [200, 409])
        self.assertEqual(StockMovement.objects.aggregate(value=Sum("quantity"))["value"], 2)
        self.assertEqual(Order.objects.filter(fulfilled_at__isnull=False).count(), 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_payments_cannot_exceed_balance(self):
        invoice = invoice_order(self.order("2"))
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
        invoice = invoice_order(self.order("2"))
        invoice.status = "issued"
        invoice.save(update_fields=["status"])
        endpoint = f"invoices/{invoice.pk}/payments/"
        payload = {"amount": "40", "request_id": str(uuid4())}
        statuses = self.run_parallel([endpoint] * 2, [payload, payload])
        self.assertEqual(statuses, [200, 200])
        self.assertEqual(Payment.objects.filter(invoice=invoice).count(), 1)
        self.assertEqual(Invoice.objects.get(pk=invoice.pk).status, "paid")
        self.assertEqual(Activity.objects.filter(resource="invoices", record_id=invoice.pk, summary__startswith="Payment ").count(), 1)

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
