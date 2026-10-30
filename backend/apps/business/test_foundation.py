from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.companies.models import Company, CompanyMembership
from .models import Activity, Contact, Invoice, Order, Payment, Product, Project, Task


class FoundationRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("foundation@example.com")
        cls.company = Company.objects.create(name="Foundation", slug="foundation")
        cls.other = Company.objects.create(name="Other", slug="foundation-other")
        for company in (cls.company, cls.other):
            CompanyMembership.objects.create(company=company, user=cls.owner, role="owner")
        cls.contact = Contact.objects.create(company=cls.company, name="Customer")
        cls.product = Product.objects.create(company=cls.company, name="Service", sku="SERVICE", kind="service", sale_price="10")

    def setUp(self):
        self.client.force_login(self.owner)
        self.base = f"/api/v1/companies/{self.company.pk}/erp/"

    def post(self, path, data, status=200):
        parts = path.strip("/").split("/")
        if parts[-1] == "actions" and parts[0] in ("orders", "invoices"):
            model = Order if parts[0] == "orders" else Invoice
            data = {"expected_version": model.objects.get(pk=parts[1]).version, **data}
        response = self.client.post(self.base + path, data, content_type="application/json")
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def test_malformed_identifiers_return_json_400(self):
        for value in ("\u00b2", "\u0661", "9" * 5000, str(2 ** 63), True, [], {}, "-1", "", 0):
            response = self.client.post(self.base + "stock/", {"product_id": value, "quantity": "1", "reason": "Audit regression"}, content_type="application/json")
            self.assertEqual(response.status_code, 400)
            self.assertIn("error", response.json())

    def test_retrying_one_payment_creates_one_completion_activity(self):
        order = self.post("orders/", {"kind": "sale", "contact_id": self.contact.pk,
            "lines": [{"product_id": self.product.pk, "quantity": "1"}]}, 201)
        self.post(f"orders/{order['id']}/actions/", {"action": "confirm"})
        invoice = self.post(f"orders/{order['id']}/actions/", {"action": "invoice"})
        self.post(f"invoices/{invoice['id']}/actions/", {"action": "issue"})
        payload = {"amount": "5", "request_id": str(uuid4())}
        self.post(f"invoices/{invoice['id']}/payments/", payload)
        self.post(f"invoices/{invoice['id']}/payments/", payload)
        self.assertEqual(Payment.objects.filter(invoice_id=invoice["id"]).count(), 1)
        self.assertEqual(Activity.objects.filter(resource="invoices", record_id=invoice["id"], summary__startswith="Payment ").count(), 1)

    def test_retaining_an_inactive_assignee_allows_other_task_edits(self):
        teammate = get_user_model().objects.create_user("former@example.com")
        membership = CompanyMembership.objects.create(company=self.company, user=teammate)
        project = Project.objects.create(company=self.company, name="Project")
        task = Task.objects.create(company=self.company, project=project, title="Original", assignee=teammate)
        membership.is_active = False
        membership.save()
        response = self.client.patch(self.base + f"tasks/{task.pk}/", {
            "title": "Updated", "project_id": project.pk, "assignee_id": teammate.pk,
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.title, "Updated")
        self.assertEqual(task.assignee_id, teammate.pk)
        self.post("tasks/", {"title": "Forbidden new assignment", "project_id": project.pk, "assignee_id": teammate.pk}, 400)

    def test_retaining_archived_company_relation_still_enforces_company_scope(self):
        self.contact.is_active = False
        self.contact.save()
        project = Project.objects.create(company=self.company, name="Project", contact=self.contact)
        response = self.client.patch(self.base + f"projects/{project.pk}/", {"name": "Updated", "contact_id": self.contact.pk}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        foreign = Contact.objects.create(company=self.other, name="Foreign", is_active=False)
        response = self.client.patch(self.base + f"projects/{project.pk}/", {"contact_id": foreign.pk}, content_type="application/json")
        self.assertEqual(response.status_code, 404)

    def test_out_of_range_pages_clamp_to_existing_results(self):
        response = self.client.get(self.base + "contacts/?page=999")
        self.assertEqual(response.json()["page"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.contact.pk)
        response = self.client.get(f"/api/v1/companies/{self.other.pk}/erp/contacts/?page=999")
        self.assertEqual(response.json()["page"], 1)
        self.assertEqual(response.json()["results"], [])
