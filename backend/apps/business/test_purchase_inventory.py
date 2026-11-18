from datetime import timedelta
from decimal import Decimal
from importlib import import_module
from types import SimpleNamespace
from uuid import uuid4

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from apps.companies.models import Company, CompanyMembership
from .models import Activity, Contact, Order, Product, PurchaseReceipt, StockMovement


class PurchaseInventoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("stock-owner@example.com")
        cls.member = get_user_model().objects.create_user("stock-reader@example.com")
        cls.company = Company.objects.create(name="Purchasing", slug="purchasing")
        cls.other = Company.objects.create(name="Foreign stock", slug="foreign-stock")
        CompanyMembership.objects.create(company=cls.company, user=cls.owner, role="owner")
        CompanyMembership.objects.create(company=cls.company, user=cls.member)
        cls.supplier = Contact.objects.create(company=cls.company, name="Supplier", is_supplier=True)
        cls.product = Product.objects.create(company=cls.company, name="Desk", sku="STOCK-DESK", cost_price="10")
        cls.service = Product.objects.create(company=cls.company, name="Setup", sku="STOCK-SERVICE", kind="service")

    def setUp(self):
        self.client.force_login(self.owner)
        self.base = f"/api/v1/companies/{self.company.pk}/erp/"

    def call(self, method, endpoint, body=None, status=200):
        response = getattr(self.client, method)(self.base + endpoint, body, content_type="application/json")
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def purchase(self, lines=None):
        order = self.call("post", "orders/", {"kind": "purchase", "contact_id": self.supplier.pk,
            "lines": lines or [{"product_id": self.product.pk, "quantity": "5"}]}, 201)
        return self.call("post", f"orders/{order['id']}/actions/", {"action": "confirm", "expected_version": order["version"]})

    def receipt(self, order, quantity="2", **overrides):
        body = {"expected_version": order["version"], "request_id": str(uuid4()),
                "lines": [{"line_id": order["lines"][0]["id"], "quantity": quantity}]}
        body.update(overrides)
        return self.call("post", f"orders/{order['id']}/receipts/", body, 201)

    def stock(self, quantity="10", **overrides):
        body = {"product_id": self.product.pk, "quantity": quantity, "reason": "Opening count", "request_id": str(uuid4())}
        body.update(overrides)
        return self.call("post", "stock/", body, 201)

    def test_partial_receipts_track_remaining_quantities_and_complete_exactly(self):
        order = self.purchase()
        partial = self.receipt(order)
        self.assertEqual(partial["order"]["receipt_status"], "partial")
        self.assertIsNone(partial["order"]["fulfilled_at"])
        self.assertEqual(partial["order"]["lines"][0]["received_quantity"], "2.000")
        self.assertEqual(partial["order"]["lines"][0]["remaining_quantity"], "3.000")
        complete = self.receipt(partial["order"], "3")
        self.assertEqual(complete["order"]["receipt_status"], "received")
        self.assertTrue(complete["order"]["fulfilled_at"])
        self.assertEqual(self.call("get", f"products/{self.product.pk}/")["stock_quantity"], "5.000")
        self.assertEqual(self.call("get", f"orders/{order['id']}/receipts/")["count"], 2)
        self.assertEqual(self.call("get", "orders/?kind=purchase")["results"][0]["receipt_status"], "received")

    def test_receipt_retry_keeps_one_batch_movement_and_activity(self):
        order = self.purchase()
        body = {"expected_version": order["version"], "request_id": str(uuid4()), "notes": "First delivery",
                "lines": [{"line_id": order["lines"][0]["id"], "quantity": "2"}]}
        first = self.call("post", f"orders/{order['id']}/receipts/", body, 201)
        second = self.call("post", f"orders/{order['id']}/receipts/", body)
        self.assertTrue(second["replayed"])
        self.assertEqual(first["receipt"], second["receipt"])
        self.assertEqual(PurchaseReceipt.objects.count(), 1)
        self.assertEqual(StockMovement.objects.count(), 1)
        self.assertEqual(Activity.objects.filter(summary__startswith="Receipt ").count(), 1)
        self.call("post", f"orders/{order['id']}/receipts/", {**body, "notes": "Changed"}, 409)

    def test_receipt_rejects_over_receipt_stale_version_and_cancellation_after_partial(self):
        order = self.purchase()
        body = {"expected_version": order["version"], "request_id": str(uuid4()),
                "lines": [{"line_id": order["lines"][0]["id"], "quantity": "6"}]}
        self.call("post", f"orders/{order['id']}/receipts/", body, 409)
        self.assertFalse(StockMovement.objects.exists())
        partial = self.receipt(order)
        self.call("post", f"orders/{order['id']}/receipts/", {**body, "lines": [{"line_id": order["lines"][0]["id"], "quantity": "1"}]}, 409)
        self.call("post", f"orders/{order['id']}/actions/", {"action": "cancel", "expected_version": partial["order"]["version"]}, 409)

    def test_full_receive_compatibility_receives_only_remaining_after_partial(self):
        order = self.purchase()
        partial = self.receipt(order)
        full = self.call("post", f"orders/{order['id']}/actions/", {"action": "fulfill", "expected_version": partial["order"]["version"]})
        self.assertTrue(full["fulfilled_at"])
        self.assertEqual(StockMovement.objects.filter(order_id=order["id"]).count(), 2)
        self.assertEqual(full["lines"][0]["received_quantity"], "5.000")

    def test_receipt_line_ids_quantities_and_request_ids_are_validated(self):
        order, other = self.purchase(), self.purchase()
        endpoint = f"orders/{order['id']}/receipts/"
        base = {"expected_version": order["version"], "request_id": str(uuid4())}
        line = {"line_id": order["lines"][0]["id"], "quantity": "1"}
        for entries in ([], [line, line], [{**line, "line_id": other["lines"][0]["id"]}],
                        [{**line, "quantity": "0"}], [{**line, "quantity": "-1"}],
                        [{**line, "quantity": "NaN"}], [{**line, "quantity": "1.0001"}],
                        [{**line, "line_id": True}], [{**line, "extra": 1}]):
            self.call("post", endpoint, {**base, "lines": entries}, 400)
        for request_id in (None, True, "bad", [], {}):
            self.call("post", endpoint, {**base, "lines": [line], "request_id": request_id}, 400)
        self.assertFalse(PurchaseReceipt.objects.exists())

    def test_duplicate_products_track_receipts_by_line_and_archived_goods_are_receivable(self):
        order = self.purchase([{"product_id": self.product.pk, "quantity": "2"}, {"product_id": self.product.pk, "quantity": "3"}])
        self.product.is_active = False
        self.product.save()
        first = self.receipt(order)
        self.assertEqual([line["received_quantity"] for line in first["order"]["lines"]], ["2.000", "0.000"])
        final = self.receipt(first["order"], lines=[{"line_id": order["lines"][1]["id"], "quantity": "3"}])
        self.assertTrue(final["order"]["fulfilled_at"])

    def test_service_only_purchase_can_be_marked_received_without_stock(self):
        order = self.purchase([{"product_id": self.service.pk, "quantity": "1"}])
        response = self.receipt(order, lines=None)
        self.assertTrue(response["order"]["fulfilled_at"])
        self.assertFalse(StockMovement.objects.exists())

    def test_supplier_return_reopens_remaining_quantity_and_accepts_replacement(self):
        order = self.purchase()
        received = self.receipt(order, "5")
        movement = received["receipt"]["movements"][0]
        body = {"quantity": "2", "reason": "Damaged on arrival", "request_id": str(uuid4())}
        result = self.call("post", f"stock/{movement['id']}/return/", body, 201)
        self.assertEqual(result["stock_quantity"], "3.000")
        reopened = self.call("get", f"orders/{order['id']}/")
        self.assertIsNone(reopened["fulfilled_at"])
        self.assertEqual(reopened["lines"][0]["remaining_quantity"], "2.000")
        self.assertTrue(self.call("post", f"stock/{movement['id']}/return/", body)["replayed"])
        self.assertEqual(StockMovement.objects.filter(return_of_id=movement["id"]).count(), 1)
        replaced = self.receipt(reopened, "2")
        self.assertTrue(replaced["order"]["fulfilled_at"])
        history = self.call("get", f"orders/{order['id']}/receipts/")
        original = next(item for item in history["results"] if item["id"] == received["receipt"]["id"])
        self.assertEqual(original["movements"][0]["returnable_quantity"], "3.000")

    def test_supplier_return_enforces_original_quantity_and_current_stock(self):
        order = self.purchase()
        received = self.receipt(order, "3")
        source = received["receipt"]["movements"][0]
        endpoint = f"stock/{source['id']}/return/"
        body = {"reason": "Return", "request_id": str(uuid4()), "quantity": "4"}
        self.call("post", endpoint, body, 409)
        self.stock("-2", reason="Stock already used")
        self.call("post", endpoint, {**body, "quantity": "2"}, 409)
        self.assertFalse(StockMovement.objects.filter(return_of_id=source["id"]).exists())

    def test_returns_cannot_target_adjustments_or_other_returns(self):
        adjustment = self.stock()
        body = {"reason": "Invalid return", "request_id": str(uuid4()), "quantity": "1"}
        self.call("post", f"stock/{adjustment['id']}/return/", body, 400)
        receipt = self.receipt(self.purchase(), "2")
        original = receipt["receipt"]["movements"][0]
        returned = self.call("post", f"stock/{original['id']}/return/", body, 201)
        self.call("post", f"stock/{returned['id']}/return/", {**body, "request_id": str(uuid4())}, 400)

    def test_adjustment_retries_create_one_movement_and_one_activity(self):
        request_id = str(uuid4())
        first = self.stock(request_id=request_id)
        body = {"product_id": self.product.pk, "quantity": "10.000", "reason": "Opening count", "request_id": request_id}
        second = self.call("post", "stock/", body)
        self.assertEqual(second["id"], first["id"])
        self.assertTrue(second["replayed"])
        self.assertEqual(StockMovement.objects.count(), 1)
        self.assertEqual(Activity.objects.count(), 1)
        self.call("post", "stock/", {**body, "quantity": "11"}, 409)
        self.product.is_active = False
        self.product.save()
        self.call("post", "stock/", body)

    def test_adjustment_reversal_preserves_history_and_is_retry_safe(self):
        first = self.stock()
        body = {"reason": "Count entered incorrectly", "request_id": str(uuid4())}
        reversed_move = self.call("post", f"stock/{first['id']}/reverse/", body, 201)
        self.assertEqual(Decimal(reversed_move["stock_quantity"]), 0)
        self.assertEqual(reversed_move["reversal_of_id"], first["id"])
        self.assertTrue(self.call("post", f"stock/{first['id']}/reverse/", body)["replayed"])
        self.call("post", f"stock/{first['id']}/reverse/", {**body, "request_id": str(uuid4())}, 409)
        original = next(item for item in self.call("get", "stock/")["results"] if item["id"] == first["id"])
        self.assertFalse(original["can_reverse"])
        self.assertEqual(original["reversed_by_id"], reversed_move["id"])

    def test_reversal_cannot_make_stock_negative_or_reverse_receipts(self):
        first = self.stock()
        self.stock("-9", reason="Consumed")
        body = {"reason": "Correction", "request_id": str(uuid4())}
        self.call("post", f"stock/{first['id']}/reverse/", body, 409)
        receipt = self.receipt(self.purchase(), "1")["receipt"]["movements"][0]
        self.call("post", f"stock/{receipt['id']}/reverse/", body, 400)

    def test_ledger_filters_search_type_dates_product_and_order(self):
        self.stock(reason="Initial count")
        order = self.purchase()
        receipt = self.receipt(order)
        self.assertEqual(self.call("get", "stock/?kind=adjustment")["count"], 1)
        self.assertEqual(self.call("get", "stock/?kind=receipt")["count"], 1)
        self.assertEqual(self.call("get", f"stock/?order_id={order['id']}")["count"], 1)
        self.assertEqual(self.call("get", f"stock/?product_id={self.product.pk}")["count"], 2)
        self.assertEqual(self.call("get", f"stock/?q={receipt['receipt']['number']}")["count"], 1)
        self.assertEqual(self.call("get", "stock/?q=initial")["count"], 1)
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.assertEqual(self.call("get", f"stock/?date_from={tomorrow}")["count"], 0)
        for query in ("kind=bad", "date_from=bad", "date_from=2026-12-01&date_to=2026-01-01"):
            self.call("get", "stock/?" + query, status=400)

    def test_company_scope_and_read_only_role_cover_receipts_returns_and_reversals(self):
        order = self.purchase()
        movement = self.stock()
        foreign = Product.objects.create(company=self.other, name="Private", sku="PRIVATE")
        self.call("get", f"stock/?product_id={foreign.pk}", status=404)
        foreign_move = StockMovement.objects.create(company=self.other, product=foreign, quantity="1", reason="Private", actor_email=self.owner.email)
        self.call("post", f"stock/{foreign_move.pk}/reverse/", {"reason": "Forbidden", "request_id": str(uuid4())}, 404)
        self.client.force_login(self.member)
        self.call("get", f"orders/{order['id']}/receipts/")
        self.call("get", "stock/")
        self.call("post", f"orders/{order['id']}/receipts/", {}, 403)
        self.call("post", f"stock/{movement['id']}/reverse/", {}, 403)
        self.call("post", f"stock/{movement['id']}/return/", {}, 403)

    def test_upgrade_links_legacy_receipts_without_changing_stock(self):
        order = self.purchase([{"product_id": self.product.pk, "quantity": "2"}, {"product_id": self.product.pk, "quantity": "2"}])
        for line in order["lines"]:
            StockMovement.objects.create(company=self.company, product=self.product, order_id=order["id"], quantity="2",
                reason="Old receipt", actor_email=self.owner.email)
        Order.objects.filter(pk=order["id"]).update(fulfilled_at=timezone.now())
        migrate = import_module("apps.business.migrations.0004_purchase_inventory_ledgers").link_existing_movements
        migrate(apps, SimpleNamespace(connection=connection))
        movements = list(StockMovement.objects.order_by("id"))
        self.assertEqual([item.order_line_id for item in movements], [line["id"] for line in order["lines"]])
        self.assertEqual([item.quantity for item in movements], [2, 2])
        self.assertTrue(all(item.receipt_id for item in movements))
        self.assertEqual(PurchaseReceipt.objects.count(), 1)
