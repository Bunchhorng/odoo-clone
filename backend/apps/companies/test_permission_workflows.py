from datetime import date
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings

from apps.business.models import Employee, Project, Task, TimesheetEntry
from apps.business.operations import save_time
from apps.business.views import orders
from apps.core.api import APIError

from .access import membership_for
from .endpoint_registry import rule_for
from .models import Company, CompanyMembership


User = get_user_model()


class PermissionWorkflowTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Workflow Co", slug="workflow-co")
        self.owner = User.objects.create_user("owner@workflow.test")
        self.admin = User.objects.create_user("admin@workflow.test")
        self.member = User.objects.create_user("member@workflow.test")
        CompanyMembership.objects.create(company=self.company, user=self.owner, role="owner")
        CompanyMembership.objects.create(company=self.company, user=self.admin, role="admin")
        CompanyMembership.objects.create(company=self.company, user=self.member, role="member")
        self.owner_employee = Employee.objects.create(
            company=self.company, user=self.owner, name="Owner", employee_code="OWNER",
        )
        self.member_employee = Employee.objects.create(
            company=self.company, user=self.member, name="Member", employee_code="MEMBER",
        )
        self.project = Project.objects.create(company=self.company, name="Project")
        self.owner_task = Task.objects.create(
            company=self.company, project=self.project, title="Owner task", assignee=self.owner,
        )
        self.entry = TimesheetEntry.objects.create(
            company=self.company, employee=self.owner_employee, project=self.project,
            date=date.today(), minutes=30, description="Submitted time", status="submitted",
            request_id=uuid4(), payload_digest="x" * 64, creator_email=self.owner.email,
        )

    def test_unqualified_orders_rule_allows_either_sales_or_purchase(self):
        request = RequestFactory().get("/api/v1/companies/1/erp/orders/")
        rule = rule_for(orders, "GET")
        self.assertEqual(rule.resolve(request, {}), (("sales", "purchase"), "read"))

    @override_settings(PERMISSION_MODE="enforce")
    def test_member_cannot_log_time_against_an_unassigned_task(self):
        with self.assertRaises(APIError) as error:
            save_time(self.member, self.company.pk, {
                "employee_id": self.member_employee.pk,
                "project_id": self.project.pk,
                "task_id": self.owner_task.pk,
                "ticket_id": None,
                "date": date.today().isoformat(),
                "minutes": 30,
                "description": "Should fail",
                "request_id": str(uuid4()),
            }, membership_for(self.member, self.company.pk))
        self.assertEqual(error.exception.status, 403)
        self.assertEqual(error.exception.message, "Choose a task assigned to you.")

    @override_settings(PERMISSION_MODE="enforce")
    def test_own_timesheet_approval_is_rejected(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            f"/api/v1/companies/{self.company.pk}/erp/timesheets/{self.entry.pk}/actions/",
            {"action": "approve", "expected_version": self.entry.version},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers["X-Permission-Code"], "self_approval_not_allowed")

    @override_settings(PERMISSION_MODE="log")
    def test_own_timesheet_approval_is_blocked_and_logged_in_log_mode(self):
        self.client.force_login(self.owner)
        route = f"/api/v1/companies/{self.company.pk}/erp/timesheets/{self.entry.pk}/actions/"
        body = {"action": "approve", "expected_version": self.entry.version}

        with self.assertLogs("kerp.permissions", level="WARNING") as logs:
            response = self.client.post(route, body, content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers["X-Permission-Code"], "self_approval_not_allowed")
        message = logs.output[0]
        self.assertIn(f"user={self.owner.pk}", message)
        self.assertIn(f"company={self.company.pk}", message)
        self.assertIn(f"route={route}", message)
        self.assertIn("action=approve", message)
        self.assertIn("reason=self_approval_not_allowed", message)

    def test_owner_cannot_review_own_time_in_any_permission_mode(self):
        self.client.force_login(self.owner)
        route = f"/api/v1/companies/{self.company.pk}/erp/timesheets/{self.entry.pk}/actions/"
        for mode in ("off", "log", "enforce"):
            for action, status in (("approve", "submitted"), ("reject", "submitted"), ("void", "approved")):
                with self.subTest(mode=mode, action=action):
                    TimesheetEntry.objects.filter(pk=self.entry.pk).update(status=status, version=1)
                    with override_settings(PERMISSION_MODE=mode):
                        response = self.client.post(
                            route,
                            {"action": action, "expected_version": 1},
                            content_type="application/json",
                        )
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(response.headers["X-Permission-Code"], "self_approval_not_allowed")

    def test_owner_and_admin_can_approve_a_members_time_in_any_permission_mode(self):
        member_entry = TimesheetEntry.objects.create(
            company=self.company, employee=self.member_employee, project=self.project,
            date=date.today(), minutes=30, description="Members submitted time", status="submitted",
            request_id=uuid4(), payload_digest="y" * 64, creator_email=self.member.email,
        )
        route = f"/api/v1/companies/{self.company.pk}/erp/timesheets/{member_entry.pk}/actions/"
        for reviewer, role in ((self.owner, "owner"), (self.admin, "admin")):
            for mode in ("off", "log", "enforce"):
                with self.subTest(role=role, mode=mode):
                    TimesheetEntry.objects.filter(pk=member_entry.pk).update(status="submitted", version=1)
                    self.client.force_login(reviewer)
                    with override_settings(PERMISSION_MODE=mode):
                        response = self.client.post(
                            route,
                            {"action": "approve", "expected_version": 1},
                            content_type="application/json",
                        )
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["status"], "approved")
