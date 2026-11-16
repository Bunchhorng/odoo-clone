from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.companies.models import Company, CompanyMembership
from .models import Contact, Invoice, InvoiceLine, Product


class PartialInvoiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("invoice-owner@example.test")
        cls.company = Company.objects.create(name="Partial invoices", slug="partial-invoices")
        CompanyMembership.objects.create(company=cls.company, user=cls.owner, role="owner")
        cls.customer = Contact.objects.create(company=cls.company, name="Customer")
        cls.product = Product.objects.create(company=cls.company, name="Desk", sku="INV-DESK")

    def setUp(self):
        self.client.force_login(self.owner); self.base = f"/api/v1/companies/{self.company.pk}/erp/"

    def call(self, method, path, body=None, status=200):
        response = getattr(self.client, method)(self.base + path, body, content_type="application/json")
        self.assertEqual(response.status_code, status, response.content); return response.json()

    def order(self):
        self.call("post", "stock/", {"product_id": self.product.pk, "quantity": "10", "reason": "opening", "request_id": str(uuid4())}, 201)
        draft = self.call("post", "orders/", {"kind": "sale", "contact_id": self.customer.pk,
            "lines": [{"product_id": self.product.pk, "quantity": "10", "unit_price": "10", "tax_rate": "7"}]}, 201)
        return self.call("post", f"orders/{draft['id']}/actions/", {"action": "confirm", "expected_version": draft["version"]})

    def deliver(self, order, amount):
        reserve = self.call("post", f"orders/{order['id']}/reservations/", {"request_id": str(uuid4()), "lines": [{"line_id": order["lines"][0]["id"], "quantity": amount}]}, 201)
        operation = self.call("post", f"orders/{order['id']}/operations/", {"request_id": str(uuid4())}, 201)["operation"]
        self.call("post", f"operations/{operation['id']}/actions/", {"action": "validate", "lines": [{"line_id": operation["lines"][0]["id"], "quantity": amount}]})

    def test_two_deliveries_create_two_immutable_allocated_invoices(self):
        order = self.order(); self.deliver(order, "6")
        first_body = {"request_id": str(uuid4()), "lines": [{"line_id": order["lines"][0]["id"], "quantity": "6"}]}
        first = self.call("post", f"orders/{order['id']}/invoices/", first_body, 201)
        self.assertEqual((first["total"], first["lines"][0]["quantity"]), ("64.20", "6.000"))
        self.call("post", f"orders/{order['id']}/invoices/", {"request_id": str(uuid4()), "lines": [{"line_id": order["lines"][0]["id"], "quantity": "1"}]}, 409)
        self.deliver(order, "4")
        second = self.call("post", f"orders/{order['id']}/invoices/", {"request_id": str(uuid4()), "lines": [{"line_id": order["lines"][0]["id"], "quantity": "4"}]}, 201)
        self.assertEqual((Invoice.objects.count(), InvoiceLine.objects.count(), second["total"]), (2, 2, "42.80"))
        self.call("post", f"orders/{order['id']}/invoices/", {"request_id": str(uuid4()), "lines": [{"line_id": order["lines"][0]["id"], "quantity": "1"}]}, 409)

    def test_undelivered_goods_cannot_be_invoiced(self):
        order = self.order()
        self.call("post", f"orders/{order['id']}/invoices/", {
            "request_id": str(uuid4()),
            "lines": [{"line_id": order["lines"][0]["id"], "quantity": "1"}],
        }, 409)

    def test_invoice_request_retry_returns_one_document(self):
        order = self.order(); self.deliver(order, "10"); request_id = str(uuid4())
        body = {"request_id": request_id, "lines": [{"line_id": order["lines"][0]["id"], "quantity": "10"}]}
        first = self.call("post", f"orders/{order['id']}/invoices/", body, 201)
        second = self.call("post", f"orders/{order['id']}/invoices/", body)
        self.assertEqual(first["id"], second["id"]); self.assertEqual(Invoice.objects.count(), 1)
