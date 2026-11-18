from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.companies.models import Company, CompanyMembership
from .models import Contact, Product, StockMovement, StockOperation, StockReservation


class DeliveryOperationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("delivery-owner@example.test")
        cls.company = Company.objects.create(name="Deliveries", slug="deliveries")
        CompanyMembership.objects.create(company=cls.company, user=cls.owner, role="owner")
        cls.customer = Contact.objects.create(company=cls.company, name="Customer")
        cls.product = Product.objects.create(company=cls.company, name="Desk", sku="DEL-DESK")

    def setUp(self):
        self.client.force_login(self.owner)
        self.base = f"/api/v1/companies/{self.company.pk}/erp/"

    def call(self, method, path, body=None, status=200):
        response = getattr(self.client, method)(self.base + path, body, content_type="application/json")
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def sale(self, quantity="10"):
        order = self.call("post", "orders/", {"kind": "sale", "contact_id": self.customer.pk,
            "lines": [{"product_id": self.product.pk, "quantity": quantity, "unit_price": "10"}]}, 201)
        return self.call("post", f"orders/{order['id']}/actions/", {"action": "confirm", "expected_version": order["version"]})

    def open_stock(self, quantity="10"):
        return self.call("post", "stock/", {"product_id": self.product.pk, "quantity": quantity,
            "reason": "Opening", "request_id": str(uuid4())}, 201)

    def reserve(self, order, quantity="10", request_id=None):
        return self.call("post", f"orders/{order['id']}/reservations/", {"request_id": request_id or str(uuid4()),
            "lines": [{"line_id": order["lines"][0]["id"], "quantity": quantity}]}, 201)

    def test_partial_validation_creates_backorder_and_posts_only_done_quantity(self):
        self.open_stock(); order = self.sale(); self.reserve(order)
        operation = self.call("post", f"orders/{order['id']}/operations/", {"request_id": str(uuid4())}, 201)["operation"]
        completed = self.call("post", f"operations/{operation['id']}/actions/", {"action": "validate",
            "lines": [{"line_id": operation["lines"][0]["id"], "quantity": "6"}]})
        self.assertEqual(completed["operation"]["status"], "done")
        self.assertEqual(completed["backorder"]["lines"][0]["planned_quantity"], "4.000")
        self.assertEqual(StockMovement.objects.get(operation_id=operation["id"]).quantity, Decimal("-6"))
        progress = self.call("get", f"orders/{order['id']}/")
        self.assertEqual(progress["lines"][0]["delivered_quantity"], "6.000")
        self.assertEqual(progress["lines"][0]["remaining_quantity"], "4.000")
        retry = self.call("post", f"operations/{operation['id']}/actions/", {"action": "validate",
            "lines": [{"line_id": operation["lines"][0]["id"], "quantity": "6"}]})
        self.assertTrue(retry["replayed"])
        self.assertEqual(StockMovement.objects.filter(operation_id=operation["id"]).count(), 1)

    def test_release_is_retry_safe_and_restores_capacity(self):
        self.open_stock("5"); order = self.sale("5"); request_id = str(uuid4()); self.reserve(order, "5", request_id)
        released = self.call("post", f"orders/{order['id']}/reservations/release/", {"request_id": request_id})
        self.assertFalse(released["replayed"])
        self.assertEqual(StockReservation.objects.get(request_id=request_id).state, "released")
        self.call("post", f"orders/{order['id']}/reservations/release/", {"request_id": request_id})
        self.reserve(order, "5")

    def test_reservations_prevent_competing_demand_and_negative_adjustment(self):
        self.open_stock("5"); first, second = self.sale("5"), self.sale("5")
        self.reserve(first, "5")
        self.call("post", f"orders/{second['id']}/reservations/", {"request_id": str(uuid4()),
            "lines": [{"line_id": second["lines"][0]["id"], "quantity": "1"}]}, 409)
        self.call("post", "stock/", {"product_id": self.product.pk, "quantity": "-1", "reason": "bad",
            "request_id": str(uuid4())}, 409)
