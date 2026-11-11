from decimal import Decimal
from importlib import import_module
from types import SimpleNamespace
from uuid import uuid4

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, transaction, IntegrityError
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Sum
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase

from apps.companies.models import Company, CompanyMembership
from .models import Contact, Product, StockLocation, StockMovement, Warehouse
from .services import stock_for


class WarehouseLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("inv01-owner@example.test")
        cls.member = get_user_model().objects.create_user("inv01-member@example.test")
        cls.company = Company.objects.create(name="INV01", slug="inv01")
        cls.other = Company.objects.create(name="Other", slug="inv01-other")
        CompanyMembership.objects.create(company=cls.company, user=cls.owner, role="owner")
        CompanyMembership.objects.create(company=cls.company, user=cls.member, role="member")
        cls.product = Product.objects.create(company=cls.company, name="Existing desk", sku="INV01-DESK")
        cls.contact = Contact.objects.create(company=cls.company, name="Partner", is_supplier=True)

    def setUp(self):
        self.client.force_login(self.owner)
        self.base = f"/api/v1/companies/{self.company.pk}/erp/"

    def call(self, method, path, data=None, status=200):
        response = getattr(self.client, method)(self.base + path, data, content_type="application/json")
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def warehouse(self, code="MAIN", **kwargs):
        return self.call("post", "warehouses/", {"name": "Warehouse", "code": code, **kwargs}, 201)

    def location(self, code, **kwargs):
        return self.call("post", "locations/", {"name": code, "code": code, **kwargs}, 201)

    def adjustment(self, quantity="8", **kwargs):
        return self.call("post", "stock/", {"product_id": self.product.pk, "quantity": quantity,
            "reason": "Existing stock API", "request_id": str(uuid4()), **kwargs}, 201)

    def test_first_warehouse_has_real_stock_root_and_virtuals(self):
        data = self.warehouse("main")
        self.assertEqual(data["code"], "MAIN")
        self.assertTrue(data["is_default"])
        root = StockLocation.objects.get(pk=data["stock_location_id"])
        self.assertEqual((root.company_id, root.usage, root.parent_id), (self.company.pk, "internal", None))
        self.assertEqual(StockLocation.objects.filter(company=self.company).count(), 4)
        self.assertEqual(self.call("get", f"warehouses/{data['id']}/")["stock_location_id"], root.pk)

    def test_warehouse_update_archive_restore_and_delete_is_non_destructive(self):
        default = self.warehouse()
        data = self.warehouse("WEST")
        updated = self.call("patch", f"warehouses/{data['id']}/", {"name": "West depot", "code": "W2"})
        self.assertEqual((updated["name"], updated["code"]), ("West depot", "W2"))
        self.call("delete", f"warehouses/{data['id']}/")
        self.assertTrue(Warehouse.objects.filter(pk=data["id"], is_active=False).exists())
        self.assertTrue(StockLocation.objects.filter(pk=data["stock_location_id"]).exists())
        self.assertEqual(self.call("get", "warehouses/?active=false")["count"], 1)
        self.call("patch", f"warehouses/{data['id']}/", {"is_active": True})
        self.call("delete", f"warehouses/{default['id']}/", status=400)
        self.assertTrue(Warehouse.objects.get(pk=default["id"]).is_active)

    def test_warehouse_validation_and_failed_create_rolls_back_auto_location(self):
        data = self.warehouse()
        before = StockLocation.objects.count()
        for body in ({"name": "Duplicate", "code": "main"}, {"name": "Bad", "code": "123"},
                     {"name": "Bad", "code": "BAD CODE"}, {"name": "Bad", "code": "X", "is_active": "false"},
                     {"name": "Bad", "code": "X", "company_id": self.other.pk}):
            self.call("post", "warehouses/", body, 400)
        self.assertEqual(StockLocation.objects.count(), before)
        foreign = StockLocation.objects.create(company=self.other, name="Foreign", code="F")
        self.call("post", "warehouses/", {"name": "Bad", "code": "BAD", "stock_location_id": foreign.pk}, 404)
        location = self.location("OTHERROOT")
        self.call("patch", f"warehouses/{data['id']}/", {"stock_location_id": location["id"]}, 400)
        child = self.location("CHILD", parent_id=data["stock_location_id"])
        self.call("post", "warehouses/", {"name": "Nested", "code": "NEST", "stock_location_id": child["id"]}, 400)

    def test_hierarchy_types_cycle_checks_and_same_company_rules(self):
        root = self.location("VIEW", usage="view")
        internal = self.location("A", parent_id=root["id"])
        child = self.location("B", parent_id=internal["id"])
        self.call("patch", f"locations/{root['id']}/", {"parent_id": child["id"]}, 400)
        self.call("patch", f"locations/{internal['id']}/", {"parent_id": internal["id"]}, 400)
        supplier = self.location("VENDOR", usage="supplier", parent_id=root["id"])
        self.location("VENDOR-CHILD", usage="supplier", parent_id=supplier["id"])
        for usage in ("internal", "customer", "inventory", "view"):
            self.call("post", "locations/", {"name": "Wrong type", "code": "WRONG", "usage": usage, "parent_id": supplier["id"]}, 400)
        foreign = StockLocation.objects.create(company=self.other, name="Foreign", code="F")
        self.call("patch", f"locations/{child['id']}/", {"parent_id": foreign.pk}, 404)
        instance = StockLocation.objects.get(pk=child["id"])
        instance.parent = foreign
        with self.assertRaises(ValidationError):
            instance.full_clean()

    def test_archive_parent_protection_and_system_location_protection(self):
        warehouse = self.warehouse()
        parent = self.location("AISLE", parent_id=warehouse["stock_location_id"])
        child = self.location("SHELF", parent_id=parent["id"])
        self.call("delete", f"locations/{parent['id']}/", status=400)
        self.call("delete", f"locations/{child['id']}/")
        self.call("delete", f"locations/{parent['id']}/")
        self.call("patch", f"locations/{child['id']}/", {"is_active": True}, 400)
        self.call("post", "locations/", {"name": "Invalid", "code": "X", "parent_id": parent["id"]}, 400)
        self.call("delete", f"locations/{warehouse['stock_location_id']}/", status=400)
        for location in StockLocation.objects.filter(company=self.company, system_key__isnull=False):
            self.call("delete", f"locations/{location.pk}/", status=400)
            self.call("patch", f"locations/{location.pk}/", {"usage": "view"}, 400)

    def test_referenced_locations_keep_identity_and_cannot_rewrite_warehouse_history(self):
        default = self.warehouse()
        self.adjustment()
        self.call("patch", f"locations/{default['stock_location_id']}/", {"usage": "customer"}, 400)
        virtual = StockLocation.objects.get(company=self.company, system_key="inventory")
        with self.assertRaises(ProtectedError):
            virtual.delete()
        node = self.location("ARCHIVE-ME")
        child = self.location("ARCHIVE-CHILD", parent_id=node["id"])
        self.call("delete", f"locations/{child['id']}/")
        self.call("delete", f"locations/{node['id']}/")
        self.assertTrue(StockLocation.objects.filter(pk=child["id"]).exists())
        self.assertTrue(StockLocation.objects.filter(pk=node["id"]).exists())

    def test_reparenting_validates_full_subtree_depth(self):
        from .locations import MAX_DEPTH
        parent = None
        for index in range(MAX_DEPTH):
            location = StockLocation(company=self.company, name=f"Level {index}", code=f"LEVEL-{index}", parent=parent)
            location.full_clean(); location.save(); parent = location
        self.call("post", "locations/", {"name": "Too deep", "code": "DEEP", "parent_id": parent.pk}, 400)
        root = self.location("SEPARATE")
        self.location("SEPARATE-CHILD", parent_id=root["id"])
        self.call("patch", f"locations/{root['id']}/", {"parent_id": parent.pk}, 400)

    def test_location_filters_pagination_and_parent_lookup_are_scoped(self):
        warehouse = self.warehouse()
        child = self.location("BIN-A", parent_id=warehouse["stock_location_id"])
        self.location("BIN-B", parent_id=child["id"])
        self.assertEqual(self.call("get", "locations/?usage=internal")["count"], 3)
        self.assertEqual(self.call("get", f"locations/?parent_id={child['id']}")["count"], 1)
        self.assertEqual(self.call("get", f"locations/?warehouse_id={warehouse['id']}")["count"], 3)
        self.assertEqual(len(self.call("get", "locations/?page_size=2")["results"]), 2)
        self.assertEqual(self.call("get", "locations/?q=BIN-B")["count"], 1)
        for query in ("usage=bad", "active=bad", "page=0", "parent_id=NaN", "warehouse_id=true"):
            self.call("get", "locations/?" + query, status=400)
        foreign = StockLocation.objects.create(company=self.other, name="Foreign", code="F")
        self.call("get", f"locations/?parent_id={foreign.pk}", status=404)
        self.call("get", f"stock/?location_id={foreign.pk}", status=404)

    def test_members_read_but_cannot_write_and_foreign_company_is_hidden(self):
        warehouse = self.warehouse()
        self.client.force_login(self.member)
        self.call("get", "warehouses/")
        self.call("get", "locations/")
        for resource, record_id in (("warehouses", warehouse["id"]), ("locations", warehouse["stock_location_id"])):
            self.call("post", f"{resource}/", {}, 403)
            self.call("patch", f"{resource}/{record_id}/", {}, 403)
            self.call("delete", f"{resource}/{record_id}/", status=403)
        foreign_base = f"/api/v1/companies/{self.other.pk}/erp/"
        self.assertEqual(self.client.get(foreign_base + "warehouses/").status_code, 404)
        self.assertEqual(self.client.get(foreign_base + "locations/").status_code, 404)
        self.client.logout()
        self.call("get", "locations/", status=401)

    def test_existing_adjustment_reversal_and_balance_contract(self):
        movement = self.adjustment()
        self.assertFalse(movement["location_inferred"])
        self.assertEqual(StockLocation.objects.get(pk=movement["source_location_id"]).usage, "inventory")
        self.assertEqual(StockLocation.objects.get(pk=movement["destination_location_id"]).usage, "internal")
        original = StockMovement.objects.get(pk=movement["id"])
        identity = (original.pk, original.quantity, original.product_id, original.created_at)
        reversed_move = self.call("post", f"stock/{original.pk}/reverse/", {"reason": "Correction", "request_id": str(uuid4())}, 201)
        self.assertEqual(reversed_move["source_location_id"], movement["destination_location_id"])
        self.assertEqual(reversed_move["destination_location_id"], movement["source_location_id"])
        self.assertEqual(stock_for(self.product), Decimal("0"))
        original.refresh_from_db()
        self.assertEqual(identity, (original.pk, original.quantity, original.product_id, original.created_at))
        self.assertEqual(self.call("get", f"stock/?location_id={movement['source_location_id']}")["count"], 2)
        with self.assertRaises(ProtectedError):
            original.destination_location.delete()

    def test_existing_receipt_return_delivery_invoice_and_reports_keep_references(self):
        def order(kind, quantity):
            data = self.call("post", "orders/", {"kind": kind, "contact_id": self.contact.pk,
                "lines": [{"product_id": self.product.pk, "quantity": quantity, "unit_price": "10"}]}, 201)
            return self.call("post", f"orders/{data['id']}/actions/", {"action": "confirm", "expected_version": data["version"]})
        purchase = order("purchase", "5")
        received = self.call("post", f"orders/{purchase['id']}/receipts/", {"request_id": str(uuid4()),
            "expected_version": purchase["version"], "lines": [{"line_id": purchase["lines"][0]["id"], "quantity": "5"}]}, 201)
        receipt_move = received["receipt"]["movements"][0]
        self.assertEqual(StockLocation.objects.get(pk=receipt_move["source_location_id"]).usage, "supplier")
        returned = self.call("post", f"stock/{receipt_move['id']}/return/", {"quantity": "1", "reason": "Damaged", "request_id": str(uuid4())}, 201)
        self.assertEqual(returned["source_location_id"], receipt_move["destination_location_id"])
        self.assertEqual(returned["receipt_id"], received["receipt"]["id"])
        sale = order("sale", "2")
        delivered = self.call("post", f"orders/{sale['id']}/actions/", {"action": "fulfill", "expected_version": sale["version"]})
        delivery = StockMovement.objects.get(order_id=sale["id"])
        self.assertEqual((delivery.source_location.usage, delivery.destination_location.usage), ("internal", "customer"))
        self.assertEqual(delivery.order_line_id, sale["lines"][0]["id"])
        invoiced = self.call("post", f"orders/{sale['id']}/actions/", {"action": "invoice", "expected_version": delivered["version"]})
        self.assertEqual(invoiced["order_id"], sale["id"])
        self.assertTrue(invoiced["id"])
        self.assertEqual(Decimal(self.call("get", f"products/{self.product.pk}/")["stock_quantity"]), 2)
        self.assertEqual(stock_for(self.product), 2)
        self.call("get", "dashboard/")
        self.call("get", "accounting/reports/")

    def test_movement_company_validation_and_bulk_non_null_constraint(self):
        stock = self.adjustment()
        foreign = StockLocation.objects.create(company=self.other, name="Foreign", code="F")
        with self.assertRaises(ValidationError):
            StockMovement.objects.create(company=self.company, product=self.product, quantity="1", reason="Invalid",
                actor_email=self.owner.email, source_location_id=foreign.pk, destination_location_id=stock["destination_location_id"])
        with self.assertRaises(IntegrityError), transaction.atomic():
            StockMovement.objects.bulk_create([StockMovement(company=self.company, product=self.product, quantity=1,
                reason="No locations", actor_email=self.owner.email)])
        self.assertEqual(StockMovement.objects.count(), 1)


class LegacyLocationMigrationTests(TransactionTestCase):
    """Exercise real schema transitions against the disposable MySQL test DB."""
    reset_sequences = True

    def test_failed_backfill_rolls_back_data_and_can_be_retried(self):
        before = [("business", "0006_service_operations")]
        schema = [("business", "0007_warehouse_location_schema")]
        target = [("business", "0009_require_stock_locations")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        old = executor.loader.project_state(before).apps
        Movement = old.get_model("business", "StockMovement")
        company = old.get_model("companies", "Company").objects.create(name="Retry", slug="inv01-retry")
        product = old.get_model("business", "Product").objects.create(company_id=company.pk, name="Retry", sku="RETRY")
        source = Movement.objects.create(company_id=company.pk, product_id=product.pk, quantity=5, reason="Original", actor_email="legacy@example.test")
        invalid = Movement.objects.create(company_id=company.pk, product_id=product.pk, quantity=7,
            reversal_of_id=source.pk, reason="Bad reversal", actor_email="legacy@example.test")
        try:
            with self.assertRaisesMessage(RuntimeError, "does not reverse"):
                MigrationExecutor(connection).migrate(target)
            current = MigrationExecutor(connection).loader.project_state(schema).apps
            self.assertEqual(current.get_model("business", "Warehouse").objects.count(), 0)
            self.assertEqual(current.get_model("business", "StockLocation").objects.count(), 0)
            self.assertEqual(current.get_model("business", "StockMovement").objects.filter(source_location__isnull=True).count(), 2)
            self.assertEqual(list(Movement.objects.order_by("pk").values_list("quantity", flat=True)), [5, 7])
        finally:
            Movement.objects.filter(pk=invalid.pk).update(quantity=-5)
            MigrationExecutor(connection).migrate(target)

    def test_foreign_company_legacy_reference_fails_before_assigning_any_locations(self):
        before = [("business", "0006_service_operations")]
        schema = [("business", "0007_warehouse_location_schema")]
        target = [("business", "0009_require_stock_locations")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        old = executor.loader.project_state(before).apps
        Company = old.get_model("companies", "Company")
        first = Company.objects.create(name="First", slug="inv01-first")
        second = Company.objects.create(name="Second", slug="inv01-second")
        product = old.get_model("business", "Product").objects.create(company_id=second.pk, name="Foreign", sku="FOREIGN")
        Movement = old.get_model("business", "StockMovement")
        invalid = Movement.objects.create(company_id=first.pk, product_id=product.pk, quantity=1,
            reason="Invalid legacy import", actor_email="legacy@example.test")
        try:
            with self.assertRaisesMessage(RuntimeError, "cross-company"):
                MigrationExecutor(connection).migrate(target)
            current = MigrationExecutor(connection).loader.project_state(schema).apps
            self.assertEqual(current.get_model("business", "Warehouse").objects.count(), 0)
            self.assertEqual(current.get_model("business", "StockLocation").objects.count(), 0)
        finally:
            Movement.objects.filter(pk=invalid.pk).update(company_id=second.pk)
            MigrationExecutor(connection).migrate(target)

    def test_upgrade_retains_ids_balances_documents_and_is_idempotent(self):
        before = [("business", "0006_service_operations")]
        target = [("business", "0009_require_stock_locations")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        old = executor.loader.project_state(before).apps
        try:
            Company = old.get_model("companies", "Company")
            Product = old.get_model("business", "Product")
            Contact = old.get_model("business", "Contact")
            Order = old.get_model("business", "Order")
            Line = old.get_model("business", "OrderLine")
            Receipt = old.get_model("business", "PurchaseReceipt")
            Movement = old.get_model("business", "StockMovement")
            company = Company.objects.create(name="Legacy", slug="legacy-inv01")
            other = Company.objects.create(name="Legacy second", slug="legacy-inv01-2")
            product = Product.objects.create(company_id=company.pk, name="Legacy", sku="LEGACY")
            partner = Contact.objects.create(company_id=company.pk, name="Partner")
            purchase = Order.objects.create(company_id=company.pk, kind="purchase", number="PO-LEGACY", contact_id=partner.pk,
                contact_name="Partner", currency="USD", status="confirmed")
            sale = Order.objects.create(company_id=company.pk, kind="sale", number="SO-LEGACY", contact_id=partner.pk,
                contact_name="Partner", currency="USD", status="confirmed")
            def line(order, quantity):
                return Line.objects.create(order_id=order.pk, product_id=product.pk, description="Legacy", product_kind="goods",
                    quantity=quantity, unit_price=10, tax_rate=0, subtotal=10, tax_total=0, total=10)
            purchase_line, sale_line = line(purchase, 5), line(sale, 2)
            receipt = Receipt.objects.create(company_id=company.pk, order_id=purchase.pk, number="REC-LEGACY",
                request_id=uuid4(), payload_digest="legacy", actor_email="legacy@example.test")
            def movement(quantity, **kwargs):
                return Movement.objects.create(company_id=company.pk, product_id=product.pk, quantity=quantity,
                    reason="Legacy history", actor_email="legacy@example.test", **kwargs)
            opening = movement(10)
            negative = movement(-1)
            received = movement(5, order_id=purchase.pk, order_line_id=purchase_line.pk, receipt_id=receipt.pk)
            delivered = movement(-2, order_id=sale.pk, order_line_id=sale_line.pk)
            returned = movement(-1, order_id=purchase.pk, order_line_id=purchase_line.pk, receipt_id=receipt.pk, return_of_id=received.pk)
            reversed_move = movement(1, reversal_of_id=negative.pk)
            zero = movement(0)
            # Preserve an unusual legacy sign without pretending it is a linked return.
            unusual = movement(1, order_id=sale.pk, order_line_id=sale_line.pk)
            columns = [field.attname for field in Movement._meta.fields]
            snapshot = list(Movement.objects.order_by("pk").values(*columns))
            quantity = Movement.objects.aggregate(value=Sum("quantity"))["value"]
            executor = MigrationExecutor(connection)
            executor.migrate(target)
            current = executor.loader.project_state(target).apps
            NewMovement = current.get_model("business", "StockMovement")
            self.assertEqual(snapshot, list(NewMovement.objects.order_by("pk").values(*columns)))
            self.assertEqual(quantity, NewMovement.objects.aggregate(value=Sum("quantity"))["value"])
            self.assertEqual(NewMovement.objects.count(), 8)
            self.assertTrue(all(NewMovement.objects.values_list("location_inferred", flat=True)))
            moves = {item.pk: item for item in NewMovement.objects.select_related("source_location", "destination_location")}
            self.assertEqual(moves[received.pk].source_location.usage, "supplier")
            self.assertEqual(moves[delivered.pk].destination_location.usage, "customer")
            self.assertEqual(moves[returned.pk].source_location_id, moves[received.pk].destination_location_id)
            self.assertEqual(moves[reversed_move.pk].destination_location_id, moves[negative.pk].source_location_id)
            self.assertEqual(moves[zero.pk].quantity, 0)
            self.assertEqual(moves[unusual.pk].destination_location.usage, "internal")
            balances = sum((abs(row.quantity) if row.destination_location.usage == "internal" else -abs(row.quantity) for row in moves.values()), Decimal(0))
            self.assertEqual(balances, quantity)
            self.assertEqual(current.get_model("business", "Warehouse").objects.count(), 2)
            self.assertEqual(current.get_model("business", "StockLocation").objects.filter(company_id=other.pk).count(), 4)
            migrate = import_module("apps.business.migrations.0008_assign_legacy_stock_locations").assign_legacy_locations
            migrate(current, SimpleNamespace(connection=connection))
            self.assertEqual(NewMovement.objects.count(), 8)
            self.assertEqual(snapshot, list(NewMovement.objects.order_by("pk").values(*columns)))
        finally:
            MigrationExecutor(connection).migrate(target)
