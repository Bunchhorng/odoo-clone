from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.companies.models import Company, CompanyMembership
from .models import Contact, CustomerReturn, Product, StockMovement, StockTransfer
from .services import stock_for


class TransfersAndCustomerReturnsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("returns-owner@example.test")
        cls.company = Company.objects.create(name="Transfers and returns", slug="transfers-returns")
        CompanyMembership.objects.create(company=cls.company, user=cls.owner, role="owner")
        cls.customer = Contact.objects.create(company=cls.company, name="Customer")
        cls.product = Product.objects.create(company=cls.company, name="Chair", sku="RET-CHAIR")

    def setUp(self):
        self.client.force_login(self.owner)
        self.base = f"/api/v1/companies/{self.company.pk}/erp/"

    def call(self, method, path, body=None, status=200):
        response = getattr(self.client, method)(self.base + path, body, content_type="application/json")
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def stock_and_warehouse(self):
        warehouse = self.call("post", "warehouses/", {"name": "Main", "code": "MAIN"}, 201)
        self.call("post", "stock/", {"product_id": self.product.pk, "quantity": "10", "reason": "Opening", "request_id": str(uuid4())}, 201)
        return warehouse

    def delivered_sale(self):
        self.stock_and_warehouse()
        draft = self.call("post", "orders/", {"kind": "sale", "contact_id": self.customer.pk,
            "lines": [{"product_id": self.product.pk, "quantity": "10", "unit_price": "10", "tax_rate": "0"}]}, 201)
        order = self.call("post", f"orders/{draft['id']}/actions/", {"action": "confirm", "expected_version": draft["version"]})
        self.call("post", f"orders/{order['id']}/reservations/", {"request_id": str(uuid4()),
            "lines": [{"line_id": order["lines"][0]["id"], "quantity": "10"}]}, 201)
        operation = self.call("post", f"orders/{order['id']}/operations/", {"request_id": str(uuid4())}, 201)["operation"]
        self.call("post", f"operations/{operation['id']}/actions/", {"action": "validate",
            "lines": [{"line_id": operation["lines"][0]["id"], "quantity": "10"}]})
        return order

    def test_partial_transfer_creates_auditable_location_movements_and_replays_safely(self):
        warehouse = self.stock_and_warehouse()
        overflow = self.call("post", "locations/", {"name": "Overflow", "code": "OVER", "usage": "internal", "is_active": True}, 201)
        body = {"request_id": str(uuid4()), "source_location_id": warehouse["stock_location_id"],
            "destination_location_id": overflow["id"], "lines": [{"product_id": self.product.pk, "quantity": "7"}]}
        created = self.call("post", "transfers/", body, 201)["transfer"]
        replay = self.call("post", "transfers/", body)["transfer"]
        self.assertEqual(created["id"], replay["id"])
        self.call("post", "transfers/", {**body, "destination_location_id": warehouse["stock_location_id"]}, 409)
        result = self.call("post", f"transfers/{created['id']}/actions/", {"action": "validate",
            "lines": [{"line_id": created["lines"][0]["id"], "quantity": "4"}]})["transfer"]
        self.assertEqual((result["status"], str(result["lines"][0]["done_quantity"])), ("done", "4.000"))
        self.assertEqual(StockMovement.objects.filter(transfer_id=created["id"]).count(), 2)
        self.assertEqual(stock_for(self.product), 10)
        self.assertEqual(StockTransfer.objects.count(), 1)

    def test_approved_restockable_return_prevents_over_return_and_preserves_delivery_history(self):
        order = self.delivered_sale()
        delivery = StockMovement.objects.get(order_id=order["id"], quantity=-10)
        body = {"request_id": str(uuid4()), "reason": "Customer changed mind", "restockable": True,
            "lines": [{"delivery_movement_id": delivery.pk, "quantity": "2"}]}
        returned = self.call("post", f"orders/{order['id']}/returns/", body, 201)["return"]
        self.assertEqual(self.call("post", f"orders/{order['id']}/returns/", body)["return"]["id"], returned["id"])
        approved = self.call("post", f"returns/{returned['id']}/actions/", {"action": "approve"})["return"]
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(stock_for(self.product), 2)
        self.assertEqual(StockMovement.objects.filter(pk=delivery.pk).count(), 1)
        self.assertEqual(CustomerReturn.objects.get(pk=returned["id"]).lines.get().movement.quantity, 2)
        self.call("post", f"orders/{order['id']}/returns/", {"request_id": str(uuid4()), "reason": "Too much", "restockable": True,
            "lines": [{"delivery_movement_id": delivery.pk, "quantity": "9"}]}, 409)

    def test_damaged_return_is_approved_without_restocking(self):
        order = self.delivered_sale()
        delivery = StockMovement.objects.get(order_id=order["id"], quantity=-10)
        returned = self.call("post", f"orders/{order['id']}/returns/", {"request_id": str(uuid4()), "reason": "Damaged", "restockable": False,
            "lines": [{"delivery_movement_id": delivery.pk, "quantity": "2"}]}, 201)["return"]
        approved = self.call("post", f"returns/{returned['id']}/actions/", {"action": "approve"})["return"]
        self.assertEqual((approved["status"], approved["lines"][0]["movement_id"], stock_for(self.product)), ("approved", None, 0))
