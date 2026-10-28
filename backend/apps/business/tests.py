from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.companies.models import Company, CompanyMembership
from .models import Activity, Contact, Invoice, Order, Payment, Product, StockMovement
from .services import invoice_order, save_order


class BusinessWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("erp-owner@example.com")
        cls.member = get_user_model().objects.create_user("erp-member@example.com")
        cls.company = Company.objects.create(name="ERP", slug="erp")
        cls.other = Company.objects.create(name="Other", slug="other-erp")
        CompanyMembership.objects.create(company=cls.company, user=cls.owner, role="owner")
        CompanyMembership.objects.create(company=cls.company, user=cls.member)
        cls.contact = Contact.objects.create(company=cls.company, name="Customer and supplier", is_supplier=True)
        cls.product = Product.objects.create(company=cls.company, name="Desk", sku="DESK", sale_price="19.99", cost_price="10.00")
        cls.foreign_contact = Contact.objects.create(company=cls.other, name="Private")
        cls.foreign_product = Product.objects.create(company=cls.other, name="Private", sku="PRIVATE")

    def setUp(self):
        self.client.force_login(self.owner)
        self.base = f"/api/v1/companies/{self.company.pk}/erp/"

    def request(self, method, endpoint, data=None, status=200):
        response = getattr(self.client, method)(self.base + endpoint, data=data, content_type="application/json")
        self.assertEqual(response.status_code, status, response.content.decode())
        return response.json()

    def create_order(self, kind="sale", quantity="2", price="19.99", tax="7.00", **overrides):
        data = {"kind": kind, "contact_id": self.contact.pk,
                "lines": [{"product_id": self.product.pk, "quantity": quantity, "unit_price": price, "tax_rate": tax}]}
        data.update(overrides)
        return self.request("post", "orders/", data, 201)

    def action(self, order_id, action, status=200):
        return self.request("post", f"orders/{order_id}/actions/", {"action": action}, status)

    def create_invoice(self, kind="sale"):
        order = self.create_order(kind)
        self.action(order["id"], "confirm")
        return self.action(order["id"], "invoice")

    def test_contact_product_search_edit_and_archive(self):
        contact = self.request("post", "contacts/", {"name": "Alice", "email": "alice@example.com"}, 201)
        self.request("patch", f"contacts/{contact['id']}/", {"phone": "123", "is_active": False})
        self.assertEqual(self.request("get", "contacts/?q=Alice")["count"], 0)
        self.assertEqual(self.request("get", "contacts/?q=Alice&active=false")["count"], 1)
        self.request("patch", f"contacts/{contact['id']}/", {"is_active": True})
        self.assertEqual(self.request("get", "contacts/?q=Alice")["count"], 1)
        product = self.request("post", "products/", {"name": "Service", "sku": "consult", "kind": "service", "sale_price": "9999999999.99"}, 201)
        self.assertEqual(product["sku"], "CONSULT")
        self.request("post", "products/", {"name": "Duplicate", "sku": "consult"}, 400)

    def test_invalid_numbers_and_fields_do_not_create_records(self):
        for value in ("-1", "NaN", "Infinity", "1.234", True, [], "1e999999"):
            self.request("post", "products/", {"name": "Bad", "sku": str(uuid4()), "sale_price": value}, 400)
        self.request("post", "contacts/", {"name": "Bad", "email": "invalid"}, 400)
        self.request("post", "contacts/", {"name": "Bad", "company_id": self.other.pk}, 400)
        self.request("post", "contacts/", {"name": "Bad", "is_active": "false"}, 400)
        self.assertEqual(Product.objects.filter(company=self.company).count(), 1)

    def test_member_is_read_only_and_inactive_membership_is_rejected(self):
        self.client.force_login(self.member)
        self.request("get", "contacts/")
        self.request("post", "contacts/", {"name": "Forbidden"}, 403)
        self.request("post", "orders/", {}, 403)
        CompanyMembership.objects.filter(user=self.member).update(is_active=False)
        self.request("get", "dashboard/", status=404)

    def test_company_and_related_record_isolation(self):
        for resource, record_id in (("contacts", self.foreign_contact.pk), ("products", self.foreign_product.pk)):
            self.request("get", f"{resource}/{record_id}/", status=404)
            self.request("patch", f"{resource}/{record_id}/", {"name": "Leak"}, 404)
        self.request("post", "orders/", {"kind": "sale", "contact_id": self.foreign_contact.pk, "lines": []}, 404)
        self.request("post", "orders/", {"kind": "sale", "contact_id": self.contact.pk,
                     "lines": [{"product_id": self.foreign_product.pk, "quantity": 1}]}, 404)
        self.request("post", "opportunities/", {"title": "Leak", "contact_id": self.foreign_contact.pk}, 404)
        response = self.client.get(f"/api/v1/companies/{self.other.pk}/erp/dashboard/")
        self.assertEqual(response.status_code, 404)

    def test_server_calculates_decimal_totals_and_snapshots(self):
        order = self.create_order(quantity="3", price="0.10", tax="7")
        self.assertEqual(Decimal(order["subtotal"]), Decimal("0.30"))
        self.assertEqual(Decimal(order["tax_total"]), Decimal("0.02"))
        self.assertEqual(Decimal(order["total"]), Decimal("0.32"))
        self.request("patch", f"products/{self.product.pk}/", {"sale_price": "100", "name": "Changed"})
        self.request("patch", f"contacts/{self.contact.pk}/", {"name": "Changed customer"})
        saved = self.request("get", f"orders/{order['id']}/")
        self.assertEqual(saved["contact_name"], "Customer and supplier")
        self.assertEqual(saved["lines"][0]["description"], "Desk")
        self.assertEqual(Decimal(saved["total"]), Decimal("0.32"))

    def test_confirmed_order_immutable_and_invalid_transitions(self):
        order = self.create_order()
        self.action(order["id"], "fulfill", 409)
        self.action(order["id"], "invoice", 409)
        self.action(order["id"], "confirm")
        self.request("patch", f"orders/{order['id']}/", {"notes": "Bad"}, 409)
        self.action(order["id"], "cancel")
        self.action(order["id"], "confirm", 409)

    def test_order_line_validation_and_atomic_rollback(self):
        for quantity in (0, -1, "0.0001", "NaN"):
            self.request("post", "orders/", {"kind": "sale", "contact_id": self.contact.pk,
                         "lines": [{"product_id": self.product.pk, "quantity": quantity}]}, 400)
        self.request("post", "orders/", {"kind": "sale", "contact_id": self.contact.pk, "lines": []}, 400)
        self.assertEqual(Order.objects.count(), 0)
        first = self.create_order()
        self.assertEqual(first["number"], "SO00001")
        self.assertEqual(self.create_order()["number"], "SO00002")

    def test_purchase_receipt_and_sale_delivery_are_idempotent(self):
        purchase = self.create_order("purchase", quantity="10")
        self.action(purchase["id"], "confirm")
        self.action(purchase["id"], "fulfill")
        self.action(purchase["id"], "fulfill")
        sale = self.create_order(quantity="3")
        self.action(sale["id"], "confirm")
        self.action(sale["id"], "fulfill")
        self.action(sale["id"], "fulfill")
        self.assertEqual(StockMovement.objects.count(), 2)
        product = self.request("get", f"products/{self.product.pk}/")
        self.assertEqual(Decimal(product["stock_quantity"]), Decimal("7"))
        self.action(sale["id"], "cancel", 409)
        self.request("patch", f"products/{self.product.pk}/", {"kind": "service"}, 409)

    def test_insufficient_stock_including_duplicate_lines_rolls_back(self):
        self.request("post", "stock/", {"product_id": self.product.pk, "quantity": "3", "reason": "Opening"}, 201)
        order = self.create_order(lines=[{"product_id": self.product.pk, "quantity": "2"}, {"product_id": self.product.pk, "quantity": "2"}])
        self.action(order["id"], "confirm")
        self.action(order["id"], "fulfill", 409)
        self.assertEqual(StockMovement.objects.count(), 1)
        self.assertIsNone(Order.objects.get(pk=order["id"]).fulfilled_at)

    def test_stock_adjustments_require_reason_and_prevent_negative_stock(self):
        self.request("post", "stock/", {"product_id": self.product.pk, "quantity": 0, "reason": "Zero"}, 400)
        self.request("post", "stock/", {"product_id": self.product.pk, "quantity": -1, "reason": "Negative"}, 409)
        self.request("post", "stock/", {"product_id": self.product.pk, "quantity": 1}, 400)
        self.request("post", "stock/", {"product_id": self.product.pk, "quantity": 5, "reason": "Opening"}, 201)
        self.request("post", "stock/", {"product_id": self.product.pk, "quantity": -2, "reason": "Count correction"}, 201)
        self.assertEqual(Decimal(self.request("get", f"products/{self.product.pk}/")["stock_quantity"]), Decimal("3"))

    def test_invoice_creation_is_idempotent_and_cancel_rules_hold(self):
        order = self.create_order()
        self.action(order["id"], "confirm")
        first = self.action(order["id"], "invoice")
        second = self.action(order["id"], "invoice")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(Invoice.objects.count(), 1)
        self.action(order["id"], "cancel", 409)
        self.request("post", f"invoices/{first['id']}/payments/", {"amount": "1"}, 409)

    def test_issue_partial_payments_full_payment_and_request_retry(self):
        invoice = self.create_invoice()
        endpoint = f"invoices/{invoice['id']}/"
        self.request("patch", endpoint, {"due_date": "2000-01-01"}, 400)
        self.request("post", endpoint + "actions/", {"action": "issue"})
        self.request("patch", endpoint, {"notes": "Locked"}, 409)
        payment = {"amount": "10.00", "request_id": str(uuid4()), "method": "bank", "reference": "First installment"}
        first = self.request("post", endpoint + "payments/", payment)
        self.request("post", endpoint + "payments/", payment)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Decimal(first["balance"]), Decimal(invoice["total"]) - 10)
        self.request("post", endpoint + "payments/", {**payment, "amount": "11"}, 409)
        self.request("post", endpoint + "payments/", {"amount": "999"}, 409)
        self.request("post", endpoint + "actions/", {"action": "cancel"}, 409)
        result = self.request("post", endpoint + "payments/", {"amount": first["balance"], "request_id": str(uuid4())})
        self.assertEqual(result["status"], "paid")
        self.assertEqual(Decimal(result["balance"]), 0)
        self.request("post", endpoint + "payments/", {"amount": "1"}, 409)

    def test_vendor_bills_and_currency_configuration(self):
        self.request("patch", "settings/", {"currency": "THB"})
        invoice = self.create_invoice("purchase")
        self.assertEqual(invoice["kind"], "vendor")
        self.assertEqual(invoice["currency"], "THB")
        self.request("patch", "settings/", {"currency": "EUR"}, 409)
        self.request("post", f"invoices/{invoice['id']}/actions/", {"action": "issue"})
        self.assertGreater(Decimal(self.request("get", "dashboard/")["payable"]), 0)

    def test_opportunity_pipeline_projects_tasks_and_assignee_scope(self):
        opportunity = self.request("post", "opportunities/", {"title": "New deal", "contact_id": self.contact.pk, "expected_revenue": "500"}, 201)
        updated = self.request("patch", f"opportunities/{opportunity['id']}/", {"stage": "won"})
        self.assertEqual(updated["probability"], 100)
        project = self.request("post", "projects/", {"name": "Implementation", "contact_id": self.contact.pk}, 201)
        task = self.request("post", "tasks/", {"title": "Configure", "project_id": project["id"], "assignee_id": self.member.pk}, 201)
        self.request("patch", f"tasks/{task['id']}/", {"stage": "done"})
        stranger = get_user_model().objects.create_user("stranger@example.com")
        self.request("patch", f"tasks/{task['id']}/", {"assignee_id": stranger.pk}, 400)
        self.assertEqual(self.request("get", "dashboard/")["open_tasks"], 0)

    def test_pagination_errors_and_activity_are_scoped(self):
        self.request("post", "contacts/", {"name": "New"}, 201)
        self.assertEqual(self.request("get", "contacts/?page_size=1")["count"], 2)
        self.assertEqual(len(self.request("get", "contacts/?page_size=1")["results"]), 1)
        for query in ("page=bad", "page=0", "page_size=101"):
            self.request("get", "contacts/?" + query, status=400)
        activity = self.request("get", "dashboard/")["activities"]
        self.assertEqual(len(activity), 1)
        self.assertEqual(Activity.objects.filter(company=self.other).count(), 0)

    def test_other_company_document_ids_cannot_be_read_or_mutated(self):
        order = save_order(self.other.pk, {"kind": "sale", "contact_id": self.foreign_contact.pk,
                           "lines": [{"product_id": self.foreign_product.pk, "quantity": "1", "unit_price": "50"}]})
        order.status = "confirmed"
        order.save(update_fields=["status"])
        invoice = invoice_order(order)
        self.request("get", f"orders/{order.pk}/", status=404)
        self.request("patch", f"orders/{order.pk}/", {"notes": "Forbidden"}, 404)
        self.request("post", f"orders/{order.pk}/actions/", {"action": "fulfill"}, 404)
        self.request("get", f"invoices/{invoice.pk}/", status=404)
        self.request("patch", f"invoices/{invoice.pk}/", {"notes": "Forbidden"}, 404)
        self.request("post", f"invoices/{invoice.pk}/actions/", {"action": "issue"}, 404)
        self.request("post", f"invoices/{invoice.pk}/payments/", {"amount": "1"}, 404)
        self.assertFalse(StockMovement.objects.exists())
        self.assertFalse(Payment.objects.exists())
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "draft")
