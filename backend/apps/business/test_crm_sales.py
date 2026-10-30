from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.companies.models import Company, CompanyMembership
from .models import Activity, Contact, Invoice, Opportunity, Order, Product


class CRMSalesWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("crm-owner@example.com")
        cls.member = get_user_model().objects.create_user("crm-member@example.com")
        cls.company = Company.objects.create(name="CRM Sales", slug="crm-sales")
        cls.other = Company.objects.create(name="Other CRM", slug="other-crm")
        CompanyMembership.objects.create(company=cls.company, user=cls.owner, role="owner")
        CompanyMembership.objects.create(company=cls.company, user=cls.member)
        cls.contact = Contact.objects.create(company=cls.company, name="Original customer")
        cls.product = Product.objects.create(company=cls.company, name="Service", sku="CRM", kind="service", sale_price="10")
        cls.opportunity = Opportunity.objects.create(company=cls.company, title="Office project", contact=cls.contact,
            stage="qualified", expected_revenue="500", notes="Agreed requirements")

    def setUp(self):
        self.client.force_login(self.owner)
        self.base = f"/api/v1/companies/{self.company.pk}/erp/"

    def call(self, method, endpoint, data=None, status=200):
        response = getattr(self.client, method)(self.base + endpoint, data, content_type="application/json")
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def quote(self, **changes):
        body = {"kind": "sale", "contact_id": self.contact.pk, "opportunity_id": self.opportunity.pk,
                "lines": [{"product_id": self.product.pk, "quantity": "1"}]}
        body.update(changes)
        return self.call("post", "orders/", body, 201)

    def action(self, order, action, status=200):
        return self.call("post", f"orders/{order['id']}/actions/",
            {"action": action, "expected_version": order["version"]}, status)

    def invoice(self):
        order = self.action(self.quote(), "confirm")
        return self.action(order, "invoice")

    def test_linked_quotations_are_traceable_and_do_not_automatically_win_the_opportunity(self):
        first, second = self.quote(), self.quote()
        self.assertEqual(first["opportunity_id"], self.opportunity.pk)
        self.assertEqual(first["opportunity_title"], "Office project")
        opportunity = self.call("get", f"opportunities/{self.opportunity.pk}/")
        self.assertEqual(opportunity["quotation_count"], 2)
        orders = self.call("get", f"orders/?opportunity_id={self.opportunity.pk}")
        self.assertEqual({item["id"] for item in orders["results"]}, {first["id"], second["id"]})
        self.action(first, "confirm")
        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.stage, "qualified")
        self.assertEqual(Activity.objects.filter(resource="opportunities", record_id=self.opportunity.pk).count(), 2)

    def test_opportunity_link_and_filters_enforce_company_and_active_scope(self):
        foreign = Opportunity.objects.create(company=self.other, title="Private deal")
        body = {"kind": "sale", "contact_id": self.contact.pk, "opportunity_id": foreign.pk,
                "lines": [{"product_id": self.product.pk, "quantity": "1"}]}
        self.call("post", "orders/", body, 404)
        self.call("get", f"orders/?opportunity_id={foreign.pk}", status=404)
        self.call("get", f"opportunities/?opportunity_id={foreign.pk}", status=404)
        for value in (True, "9" * 5000, [], "bad"):
            self.call("post", "orders/", {**body, "opportunity_id": value}, 400)
        self.call("post", "orders/", {**body, "kind": "purchase", "opportunity_id": self.opportunity.pk}, 400)
        self.opportunity.is_active = False
        self.opportunity.save()
        self.call("post", "orders/", {**body, "opportunity_id": self.opportunity.pk}, 400)
        self.assertFalse(Order.objects.exists())

    def test_link_cannot_be_reassigned_and_archiving_preserves_existing_links(self):
        order = self.quote()
        other = Opportunity.objects.create(company=self.company, title="Different deal")
        self.call("patch", f"orders/{order['id']}/", {"opportunity_id": other.pk, "expected_version": order["version"]}, 400)
        self.opportunity.is_active = False
        self.opportunity.save()
        changed = self.call("patch", f"orders/{order['id']}/", {"notes": "Still editable", "expected_version": order["version"]})
        self.assertEqual(changed["opportunity_id"], self.opportunity.pk)
        results = self.call("get", f"opportunities/?opportunity_id={self.opportunity.pk}&active=all")["results"]
        self.assertEqual(results[0]["quotation_count"], 1)

    def test_member_can_follow_links_but_cannot_create_or_restore(self):
        order = self.quote()
        invoice = self.action(self.action(order, "confirm"), "invoice")
        self.client.force_login(self.member)
        self.assertEqual(self.call("get", f"orders/?opportunity_id={self.opportunity.pk}")["count"], 1)
        self.assertEqual(self.call("get", f"opportunities/{self.opportunity.pk}/")["quotation_count"], 1)
        self.call("post", "orders/", {"opportunity_id": self.opportunity.pk}, 403)
        self.call("post", f"invoices/{invoice['id']}/actions/", {"action": "restore", "expected_version": invoice["version"]}, 403)

    def test_missing_or_invalid_versions_cannot_edit_or_confirm_drafts(self):
        order = self.quote()
        for value in (None, True, "1", 0, -1, [], {}):
            for method, endpoint, fields in (("patch", f"orders/{order['id']}/", {"notes": "Unsafe"}),
                                            ("post", f"orders/{order['id']}/actions/", {"action": "confirm"})):
                self.call(method, endpoint, {**fields, "expected_version": value}, 400)
        self.assertEqual(Order.objects.get(pk=order["id"]).status, "draft")

    def test_stale_order_save_and_confirmation_leave_latest_values_unchanged(self):
        original = self.quote()
        updated = self.call("patch", f"orders/{original['id']}/", {"expected_version": original["version"],
            "lines": [{"product_id": self.product.pk, "quantity": "1", "unit_price": "100"}]})
        self.assertEqual(updated["version"], original["version"] + 1)
        self.call("patch", f"orders/{original['id']}/", {"notes": "Old editor", "expected_version": original["version"]}, 409)
        self.action(original, "confirm", 409)
        saved = self.call("get", f"orders/{original['id']}/")
        self.assertEqual(saved["total"], "100.00")
        self.assertEqual(saved["status"], "draft")
        self.assertEqual(self.action(updated, "confirm")["total"], "100.00")

    def test_transition_retries_leave_one_completion_activity_and_unchanged_version(self):
        order = self.quote()
        for action in ("confirm", "fulfill", "invoice"):
            before = Activity.objects.count()
            first = self.action(order, action)
            second = self.action(order, action)  # Retry with the original request/version.
            self.assertEqual(first, second)
            self.assertEqual(Activity.objects.count(), before + 1)
            if action != "invoice":
                order = first
        self.assertEqual(Invoice.objects.count(), 1)

    def test_stale_delivery_and_invoice_requests_do_not_perform_new_transitions(self):
        draft = self.quote()
        confirmed = self.action(draft, "confirm")
        self.action(draft, "fulfill", 409)
        self.action(draft, "invoice", 409)
        self.assertFalse(Invoice.objects.exists())
        self.assertIsNone(Order.objects.get(pk=draft["id"]).fulfilled_at)
        self.action(confirmed, "fulfill")

    def test_archived_contact_can_be_retained_without_refreshing_its_snapshot(self):
        order = self.quote()
        self.contact.is_active = False
        self.contact.is_customer = False
        self.contact.name = "Renamed archived contact"
        self.contact.save()
        updated = self.call("patch", f"orders/{order['id']}/", {"contact_id": self.contact.pk,
            "notes": "Updated terms", "expected_version": order["version"]})
        self.assertEqual(updated["contact_name"], "Original customer")
        self.assertEqual(updated["notes"], "Updated terms")
        foreign = Contact.objects.create(company=self.other, name="Foreign", is_active=False)
        self.call("patch", f"orders/{order['id']}/", {"contact_id": foreign.pk, "expected_version": updated["version"]}, 404)
        self.call("post", "orders/", {"kind": "sale", "contact_id": self.contact.pk,
            "lines": [{"product_id": self.product.pk, "quantity": "1"}]}, 400)

    def test_archived_products_can_be_retained_on_existing_lines_but_not_added(self):
        order = self.quote()
        self.product.is_active = False
        self.product.save()
        changed = self.call("patch", f"orders/{order['id']}/", {"notes": "Notes only", "expected_version": order["version"]})
        line = {key: changed["lines"][0][key] for key in ("id", "product_id", "description", "quantity", "unit_price", "tax_rate")}
        updated = self.call("patch", f"orders/{order['id']}/", {"lines": [{**line, "quantity": "2"}], "expected_version": changed["version"]})
        self.assertEqual(updated["lines"][0]["id"], line["id"])
        self.assertEqual(updated["total"], "20.00")
        new_line = {key: value for key, value in line.items() if key != "id"}
        self.call("patch", f"orders/{order['id']}/", {"lines": [line, new_line], "expected_version": updated["version"]}, 400)
        self.call("patch", f"orders/{order['id']}/", {"lines": [line, line], "expected_version": updated["version"]}, 400)

    def test_order_line_ids_cannot_reference_another_order(self):
        first, second = self.quote(), self.quote()
        self.call("patch", f"orders/{second['id']}/", {"expected_version": second["version"],
            "lines": [{"id": first["lines"][0]["id"], "product_id": self.product.pk, "quantity": "1"}]}, 400)

    def test_stale_invoice_edits_and_issue_are_rejected(self):
        invoice = self.invoice()
        updated = self.call("patch", f"invoices/{invoice['id']}/", {"notes": "New terms", "expected_version": invoice["version"]})
        self.call("patch", f"invoices/{invoice['id']}/", {"notes": "Stale terms", "expected_version": invoice["version"]}, 409)
        self.call("post", f"invoices/{invoice['id']}/actions/", {"action": "issue", "expected_version": invoice["version"]}, 409)
        self.assertEqual(Invoice.objects.get(pk=invoice["id"]).status, "draft")
        self.call("post", f"invoices/{invoice['id']}/actions/", {"action": "issue", "expected_version": updated["version"]})

    def test_cancelled_unpaid_invoice_can_return_to_draft_with_history(self):
        invoice = self.invoice()
        endpoint = f"invoices/{invoice['id']}/actions/"
        issued = self.call("post", endpoint, {"action": "issue", "expected_version": invoice["version"]})
        cancelled = self.call("post", endpoint, {"action": "cancel", "expected_version": issued["version"]})
        before = Activity.objects.count()
        retried = self.call("post", endpoint, {"action": "cancel", "expected_version": issued["version"]})
        self.assertEqual(retried, cancelled)
        self.assertEqual(Activity.objects.count(), before)
        self.call("post", endpoint, {"action": "restore", "expected_version": issued["version"]}, 409)
        restored = self.call("post", endpoint, {"action": "restore", "expected_version": cancelled["version"]})
        self.assertEqual(restored["status"], "draft")
        self.assertEqual(restored["number"], invoice["number"])
        self.call("patch", f"invoices/{invoice['id']}/", {"notes": "Corrected terms", "expected_version": restored["version"]})
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(Activity.objects.filter(summary__startswith="Restore:").count(), 1)

    def test_paid_documents_cannot_be_restored_or_cancelled(self):
        invoice = self.invoice()
        endpoint = f"invoices/{invoice['id']}/actions/"
        issued = self.call("post", endpoint, {"action": "issue", "expected_version": invoice["version"]})
        paid = self.call("post", f"invoices/{invoice['id']}/payments/", {"amount": issued["total"]})
        self.assertGreater(paid["version"], issued["version"])
        for action in ("restore", "cancel"):
            self.call("post", endpoint, {"action": action, "expected_version": paid["version"]}, 409)
        self.assertEqual(Invoice.objects.get(pk=invoice["id"]).status, "paid")
