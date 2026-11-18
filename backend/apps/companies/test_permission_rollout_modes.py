from uuid import uuid4
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from apps.business.models import Activity, Contact, Employee, Order, Project, Task, TimesheetEntry

from .models import Company, CompanyAccessGroup, CompanyAccessGroupMembership, CompanyMembership
from .permission_audit import audit_request
from .seeding import seed_company, sync_membership_system_groups


User = get_user_model()


class PermissionRolloutModeTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Rollout Co", slug="rollout-co")
        self.owner = User.objects.create_user("owner@rollout.test")
        self.member = User.objects.create_user("member@rollout.test")
        self.purchase_member = User.objects.create_user("purchase@rollout.test")
        self.owner_membership = CompanyMembership.objects.create(company=self.company, user=self.owner, role="owner")
        self.member_membership = CompanyMembership.objects.create(company=self.company, user=self.member, role="member")
        self.purchase_membership = CompanyMembership.objects.create(company=self.company, user=self.purchase_member, role="member")
        sync_membership_system_groups(self.member_membership)
        groups = sync_membership_system_groups(self.purchase_membership)
        CompanyAccessGroupMembership.objects.create(user=self.purchase_member, group=groups["purchase-user"])
        self.contact = Contact.objects.create(company=self.company, name="Customer")
        self.order = Order.objects.create(
            company=self.company, kind="sale", number="SO-ROLL", contact=self.contact,
            contact_name=self.contact.name, currency="USD",
        )
        self.member_employee = Employee.objects.create(company=self.company, user=self.member, name="Member", employee_code="MEM")
        self.owner_employee = Employee.objects.create(company=self.company, user=self.owner, name="Owner", employee_code="OWN")
        self.project = Project.objects.create(company=self.company, name="Project")
        self.other_task = Task.objects.create(company=self.company, project=self.project, title="Other task", assignee=self.owner)
        self.self_time = TimesheetEntry.objects.create(
            company=self.company, employee=self.owner_employee, project=self.project,
            date=timezone.localdate(), minutes=30, description="Own submitted time", status="submitted",
            request_id=uuid4(), payload_digest="x" * 64, creator_email=self.owner.email,
        )
        # Activity and order primary keys come from independent sequences.  A
        # deleted probe keeps this test from accidentally relying on equality.
        Activity.objects.create(company=self.company, resource="probe", record_id=0,
                                actor_email=self.owner.email, summary="Sequence probe").delete()
        Activity.objects.create(company=self.company, resource="orders", record_id=self.order.pk,
                                actor_email=self.owner.email, summary="Created SO-ROLL")
        self.base = f"/api/v1/companies/{self.company.pk}/erp/"

    def call(self, method, endpoint, data=None):
        return getattr(self.client, method)(self.base + endpoint, data, content_type="application/json")

    def log_messages(self, callback):
        with self.assertLogs("kerp.permissions", level="WARNING") as logs:
            response = callback()
        return response, "\n".join(logs.output)

    @override_settings(PERMISSION_MODE="log")
    def test_log_orders_list_keeps_legacy_response_and_logs_hidden_records(self):
        self.client.force_login(self.purchase_member)
        response, logs = self.log_messages(lambda: self.call("get", "orders/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["id"], self.order.pk)
        self.assertIn("reason=no_app_access", logs)
        self.assertIn("hidden_records=1", logs)

    @override_settings(PERMISSION_MODE="enforce")
    def test_enforce_orders_list_hides_disallowed_kind(self):
        self.client.force_login(self.purchase_member)
        response = self.call("get", "orders/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

    @override_settings(PERMISSION_MODE="log")
    def test_log_unassigned_task_keeps_legacy_success_and_logs(self):
        self.client.force_login(self.member)
        response, logs = self.log_messages(lambda: self.call("post", "timesheets/", {
            "employee_id": self.member_employee.pk, "project_id": self.project.pk, "task_id": self.other_task.pk,
            "date": timezone.localdate().isoformat(), "minutes": 30, "description": "Legacy success", "request_id": str(uuid4()),
        }))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["task_id"], self.other_task.pk)
        self.assertIn("reason=task_not_assigned", logs)

    @override_settings(PERMISSION_MODE="enforce")
    def test_enforce_unassigned_task_returns_403(self):
        self.client.force_login(self.member)
        response = self.call("post", "timesheets/", {
            "employee_id": self.member_employee.pk, "project_id": self.project.pk, "task_id": self.other_task.pk,
            "date": timezone.localdate().isoformat(), "minutes": 30, "description": "Denied", "request_id": str(uuid4()),
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers["X-Permission-Code"], "task_not_assigned")

    @override_settings(PERMISSION_MODE="log")
    def test_log_dashboard_keeps_legacy_activity_and_logs_hidden_records(self):
        self.client.force_login(self.member)
        response, logs = self.log_messages(lambda: self.call("get", "dashboard/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["resource"] for item in response.json()["activities"]], ["orders"])
        self.assertIn("reason=no_app_access", logs)
        self.assertIn("hidden_records=1", logs)

    @override_settings(PERMISSION_MODE="enforce")
    def test_enforce_dashboard_hides_unread_activity(self):
        self.client.force_login(self.member)
        response = self.call("get", "dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["activities"], [])

    @override_settings(PERMISSION_MODE="log")
    def test_log_self_approval_is_blocked_and_logs(self):
        self.client.force_login(self.owner)
        response, logs = self.log_messages(lambda: self.call("post", f"timesheets/{self.self_time.pk}/actions/", {
            "action": "approve", "expected_version": self.self_time.version,
        }))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers["X-Permission-Code"], "self_approval_not_allowed")
        self.assertIn("reason=self_approval_not_allowed", logs)

    @override_settings(PERMISSION_MODE="enforce")
    def test_enforce_self_approval_returns_403(self):
        self.client.force_login(self.owner)
        response = self.call("post", f"timesheets/{self.self_time.pk}/actions/", {
            "action": "approve", "expected_version": self.self_time.version,
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers["X-Permission-Code"], "self_approval_not_allowed")

    def test_member_off_and_log_responses_are_identical_for_gated_get_endpoints(self):
        self.client.force_login(self.member)
        with override_settings(PERMISSION_MODE="off"):
            off_orders = self.call("get", "orders/").json()
            off_dashboard = self.call("get", "dashboard/").json()
            off_timesheets = self.call("get", "timesheets/").json()
        with override_settings(PERMISSION_MODE="log"):
            log_orders = self.call("get", "orders/").json()
            log_dashboard = self.call("get", "dashboard/").json()
            log_timesheets = self.call("get", "timesheets/").json()
        self.assertEqual(log_orders, off_orders)
        self.assertEqual(log_dashboard, off_dashboard)
        self.assertEqual(log_timesheets, off_timesheets)

    @override_settings(PERMISSION_MODE="off")
    def test_timesheet_lookup_fields_are_additive_without_changing_existing_fields(self):
        self.client.force_login(self.member)
        response = self.call("get", "timesheets/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual({key: payload[key] for key in ("results", "count", "page", "page_size", "summary", "can_log")}, {
            "results": [], "count": 0, "page": 1, "page_size": 25,
            "summary": {"total_minutes": 0, "approved_minutes": 0, "submitted_minutes": 0}, "can_log": True,
        })
        self.assertEqual(set(payload) - {"results", "count", "page", "page_size", "summary", "can_log"},
                         {"employees", "projects", "tasks", "tickets"})

    @override_settings(PERMISSION_MODE="off")
    def test_off_mode_permission_gates_add_no_queries(self):
        request = RequestFactory().get("/api/v1/companies/1/erp/dashboard/")
        request.user = type("User", (), {"pk": 1, "is_authenticated": True})()
        view = type("View", (), {"__module__": "apps.business.views", "__name__": "dashboard"})
        with self.assertNumQueries(0):
            audit_request(request, view, {"company_id": 1})
        self.client.force_login(self.member)
        with patch("apps.business.views.resolve_effective_access") as resolved:
            self.call("get", "orders/")
            self.call("get", "dashboard/")
        resolved.assert_not_called()
