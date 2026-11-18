import csv
import io
from datetime import timedelta
from uuid import uuid4

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.companies.models import Company, CompanyMembership
from .models import Activity, Contact, Department, Employee, HelpdeskTicket, JournalEntry, Project, Task, TicketMessage, TimesheetEntry


class ServiceOperationsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("ops-owner@example.test")
        cls.member = get_user_model().objects.create_user("ops-member@example.test")
        cls.other_member = get_user_model().objects.create_user("ops-other@example.test")
        cls.company = Company.objects.create(name="Services", slug="services")
        cls.other = Company.objects.create(name="Other services", slug="other-services")
        for user, role in ((cls.owner, "owner"), (cls.member, "member"), (cls.other_member, "member")):
            CompanyMembership.objects.create(company=cls.company, user=user, role=role)
        cls.department = Department.objects.create(company=cls.company, name="Support")
        cls.employee = Employee.objects.create(company=cls.company, name="Team member", employee_code="MEM", user=cls.member, department=cls.department)
        cls.owner_employee = Employee.objects.create(company=cls.company, name="Owner", employee_code="OWN", user=cls.owner)
        cls.project = Project.objects.create(company=cls.company, name="Installation")
        cls.project2 = Project.objects.create(company=cls.company, name="Maintenance")
        cls.task = Task.objects.create(company=cls.company, project=cls.project, title="Install")
        cls.contact = Contact.objects.create(company=cls.company, name="Service customer")

    def setUp(self):
        self.client.force_login(self.owner)
        self.base = f"/api/v1/companies/{self.company.pk}/erp/"

    def call(self, method, endpoint, data=None, status=200):
        result = getattr(self.client, method)(self.base + endpoint, data, content_type="application/json")
        self.assertEqual(result.status_code, status, result.content)
        return result.json()

    def ticket(self, **fields):
        return self.call("post", "helpdesk/", {"title": "Customer setup", "project_id": self.project.pk,
            "contact_id": self.contact.pk, "request_id": str(uuid4()), **fields}, 201)

    def ticket_action(self, item, name, status=200, **fields):
        return self.call("post", f"helpdesk/{item['id']}/actions/", {"action": name, "expected_version": item["version"], **fields}, status)

    def time(self, **fields):
        return self.call("post", "timesheets/", {"employee_id": self.employee.pk, "project_id": self.project.pk,
            "task_id": self.task.pk, "date": timezone.localdate().isoformat(), "minutes": 60,
            "description": "Installation work", "request_id": str(uuid4()), **fields}, 201)

    def time_action(self, item, name, status=200, **fields):
        return self.call("post", f"timesheets/{item['id']}/actions/", {"action": name, "expected_version": item["version"], **fields}, status)

    def test_employee_directory_department_account_links_and_unique_codes(self):
        employee = self.call("post", "employees/", {"name": "Specialist", "employee_code": " staff-1 ", "work_email": "work@example.test",
            "department_id": self.department.pk, "user_id": self.other_member.pk}, 201)
        self.assertEqual(employee["employee_code"], "STAFF-1")
        self.assertEqual(employee["department_name"], "Support")
        self.call("post", "employees/", {"name": "Duplicate", "employee_code": "staff-1"}, 400)
        self.call("post", "employees/", {"name": "Duplicate account", "employee_code": "NEW", "user_id": self.member.pk}, 400)
        self.assertEqual(self.call("get", f"employees/?department_id={self.department.pk}&q=staff-1")["count"], 1)

    def test_employee_relations_are_scoped_and_archived_department_can_be_retained(self):
        foreign = Department.objects.create(company=self.other, name="Private department")
        self.call("patch", f"employees/{self.employee.pk}/", {"department_id": foreign.pk}, 404)
        foreign_user = get_user_model().objects.create_user("private-employee@example.test")
        CompanyMembership.objects.create(company=self.other, user=foreign_user)
        self.call("patch", f"employees/{self.employee.pk}/", {"user_id": foreign_user.pk}, 400)
        self.department.is_active = False; self.department.save()
        self.call("patch", f"employees/{self.employee.pk}/", {"department_id": self.department.pk, "job_title": "Technician"})
        self.call("post", "employees/", {"name": "New", "employee_code": "NEW", "department_id": self.department.pk}, 400)

    def test_members_read_directory_but_cannot_manage_employees_or_departments(self):
        self.client.force_login(self.member)
        self.assertEqual(self.call("get", "employees/")["count"], 2)
        self.call("post", "employees/", {"name": "Unauthorized"}, 403)
        self.call("patch", f"employees/{self.employee.pk}/", {"user_id": self.owner.pk}, 403)
        self.call("post", "departments/", {"name": "Unauthorized"}, 403)

    def test_member_logs_submits_and_reads_only_own_time(self):
        other = self.time(employee_id=self.owner_employee.pk)
        self.client.force_login(self.member)
        own = self.time()
        self.assertEqual(self.call("get", "timesheets/")["count"], 1)
        self.call("get", f"timesheets/{other['id']}/", status=404)
        self.call("post", "timesheets/", {"employee_id": self.owner_employee.pk, "project_id": self.project.pk,
            "date": timezone.localdate().isoformat(), "minutes": 10, "description": "Forged", "request_id": str(uuid4())}, 403)
        submitted = self.time_action(own, "submit")
        self.assertEqual(submitted["status"], "submitted")
        self.time_action(submitted, "approve", 403)
        self.time_action(submitted, "reject", 403, reason="Forged review")
        self.call("patch", f"timesheets/{own['id']}/", {"minutes": 120, "expected_version": submitted["version"]}, 409)
        draft = self.time_action(submitted, "withdraw")
        discarded = self.time_action(draft, "discard", reason="Accidental draft")
        self.assertEqual(discarded["status"], "voided")
        self.assertEqual(self.call("get", "timesheets/")["summary"]["total_minutes"], 0)

    def test_time_review_rejection_correction_approval_and_void_preserve_record(self):
        entry = self.time()
        submitted = self.time_action(entry, "submit")
        self.time_action(submitted, "reject", 400, reason="")
        rejected = self.time_action(submitted, "reject", reason="Explain work")
        self.assertEqual(rejected["review_note"], "Explain work")
        corrected = self.call("patch", f"timesheets/{entry['id']}/", {"description": "Installed workstations", "expected_version": rejected["version"]})
        approved = self.time_action(self.time_action(corrected, "submit"), "approve")
        self.assertEqual(approved["status"], "approved")
        self.call("patch", f"timesheets/{entry['id']}/", {"minutes": 5, "expected_version": approved["version"]}, 409)
        self.assertEqual(self.call("get", "timesheets/")["summary"]["approved_minutes"], 60)
        voided = self.time_action(approved, "void", reason="Recorded on wrong project")
        self.assertEqual(voided["minutes"], 60)
        self.assertEqual(voided["status"], "voided")
        self.assertEqual(self.call("get", "timesheets/")["summary"]["total_minutes"], 0)
        self.assertEqual(TimesheetEntry.objects.count(), 1)
        self.assertFalse(JournalEntry.objects.exists())

    def test_time_creation_retry_and_conflicting_uuid(self):
        token = str(uuid4())
        original = self.time(request_id=token)
        body = {"employee_id": self.employee.pk, "project_id": self.project.pk, "task_id": self.task.pk,
            "date": timezone.localdate().isoformat(), "minutes": 60, "description": "Installation work", "request_id": token}
        self.assertEqual(self.call("post", "timesheets/", body)["id"], original["id"])
        self.call("post", "timesheets/", {**body, "minutes": 61}, 409)
        self.assertEqual(TimesheetEntry.objects.count(), 1)
        self.assertEqual(Activity.objects.filter(resource="timesheets").count(), 1)

    def test_time_minutes_daily_bound_and_date_validation(self):
        entry = self.time(minutes=1400)
        base = {"employee_id": self.employee.pk, "project_id": self.project.pk, "date": timezone.localdate().isoformat(),
            "minutes": 41, "description": "Extra work", "request_id": str(uuid4())}
        self.call("post", "timesheets/", base, 409)
        for value in (0, -1, 1441, True, "60", 1.5):
            self.call("post", "timesheets/", {**base, "minutes": value}, 400)
        self.call("post", "timesheets/", {**base, "minutes": 40, "date": (timezone.localdate() + timedelta(days=1)).isoformat()}, 400)
        self.time(minutes=40)
        self.call("patch", f"timesheets/{entry['id']}/", {"minutes": 1440, "expected_version": entry["version"]}, 409)
        self.time_action(entry, "discard", reason="Entered in error")
        self.time(minutes=1400)

    def test_time_task_project_ticket_scope_and_active_retention(self):
        ticket = self.ticket_action(self.ticket(), "create_task")
        body = {"employee_id": self.employee.pk, "project_id": self.project.pk, "task_id": self.task.pk, "ticket_id": ticket["id"],
            "date": timezone.localdate().isoformat(), "minutes": 20, "description": "Support", "request_id": str(uuid4())}
        self.call("post", "timesheets/", body, 400)
        self.call("post", "timesheets/", {**body, "task_id": ticket["task_id"], "project_id": self.project2.pk}, 400)
        entry = self.call("post", "timesheets/", {**body, "task_id": ticket["task_id"]}, 201)
        self.project.is_active = False; self.project.save()
        self.call("patch", f"timesheets/{entry['id']}/", {"description": "Historical correction", "expected_version": entry["version"]})
        self.call("post", "timesheets/", {**body, "ticket_id": None, "request_id": str(uuid4())}, 400)
        private = Employee.objects.create(company=self.other, name="Private", employee_code="PRIVATE")
        self.call("post", "timesheets/", {**body, "employee_id": private.pk, "request_id": str(uuid4())}, 404)
        self.call("get", f"timesheets/?employee_id={private.pk}", status=404)

    def test_employee_account_and_task_project_are_fixed_after_time_is_logged(self):
        self.time()
        self.call("patch", f"employees/{self.employee.pk}/", {"user_id": self.other_member.pk}, 409)
        self.call("patch", f"tasks/{self.task.pk}/", {"project_id": self.project2.pk}, 409)
        self.call("patch", f"employees/{self.employee.pk}/", {"job_title": "Senior specialist"})

    def test_time_stale_versions_cannot_overwrite_or_approve_unseen_changes(self):
        entry = self.time()
        for invalid in (None, [], {}, True):
            self.time_action(entry, invalid, 400)
        changed = self.call("patch", f"timesheets/{entry['id']}/", {"minutes": 90, "expected_version": entry["version"]})
        self.time_action(entry, "submit", 409)
        submitted = self.time_action(changed, "submit")
        self.time_action(submitted, "approve")
        self.time_action(submitted, "approve", 409)
        self.assertEqual(Activity.objects.filter(summary__startswith="Approve time").count(), 1)

    def test_time_filters_summaries_and_export_respect_member_scope(self):
        self.time(employee_id=self.owner_employee.pk, minutes=120)
        self.time(description="=1+1", minutes=30)
        self.client.force_login(self.member)
        listing = self.call("get", f"timesheets/?project_id={self.project.pk}&q=1%2B1")
        self.assertEqual(listing["summary"]["total_minutes"], 30)
        response = self.client.get(self.base + "timesheets/export/")
        self.assertEqual(response.status_code, 200)
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 2)
        self.assertIn("'=1+1", rows[1])
        self.assertNotIn("Owner", rows[1])
        activity = self.call("get", "dashboard/")["activities"]
        self.assertTrue(any("30 minutes" in row["summary"] for row in activity))
        self.assertFalse(any("120 minutes" in row["summary"] for row in activity))
        for query in ("status=bad", "date_from=bad", "date_from=2026-02-01&date_to=2026-01-01", "employee_id=" + "9" * 30):
            self.call("get", "timesheets/?" + query, status=400)

    def test_ticket_creation_assignment_and_comment_retries(self):
        token = str(uuid4())
        body = {"title": "Printer setup", "request_id": token, "assignee_id": self.member.pk}
        item = self.call("post", "helpdesk/", body, 201)
        self.assertEqual(self.call("post", "helpdesk/", body)["id"], item["id"])
        self.call("post", "helpdesk/", {**body, "title": "Different"}, 409)
        note = {"body": "Initial diagnosis", "request_id": str(uuid4())}
        first = self.call("post", f"helpdesk/{item['id']}/messages/", note, 201)
        self.assertEqual(self.call("post", f"helpdesk/{item['id']}/messages/", note)["id"], first["id"])
        self.call("post", f"helpdesk/{item['id']}/messages/", {**note, "body": "Changed"}, 409)
        self.assertEqual(HelpdeskTicket.objects.count(), 1)
        self.assertEqual(TicketMessage.objects.count(), 1)

    def test_member_ticket_creation_own_new_edits_and_comments_without_assignment_privileges(self):
        private = self.ticket()
        self.client.force_login(self.member)
        item = self.ticket()
        self.call("patch", f"helpdesk/{item['id']}/", {"title": "More details", "expected_version": item["version"]})
        self.call("patch", f"helpdesk/{private['id']}/", {"title": "Unowned edit", "expected_version": private["version"]}, 403)
        self.call("post", "helpdesk/", {"title": "Assign others", "request_id": str(uuid4()), "assignee_id": self.owner.pk}, 403)
        self.ticket_action(item, "resolve", 403, resolution="Unauthorized")
        self.call("post", f"helpdesk/{private['id']}/messages/", {"body": "Follow-up", "request_id": str(uuid4())}, 201)

    def test_resolution_reopen_and_new_resolution_retain_full_history(self):
        item = self.ticket()
        self.ticket_action(item, "resolve", 400, resolution="")
        resolved = self.ticket_action(item, "resolve", resolution="First resolution " + "a" * 1000)
        self.assertIsNotNone(resolved["resolved_at"])
        reopened = self.ticket_action(resolved, "reopen")
        self.assertIsNone(reopened["resolved_at"])
        self.ticket_action(reopened, "resolve", resolution="Second resolution")
        messages = self.call("get", f"helpdesk/{item['id']}/messages/")["results"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(len(messages[1]["body"]), 1017)
        self.assertTrue(all(message["kind"] == "resolution" for message in messages))

    def test_ticket_task_conversion_retries_and_project_immutability(self):
        item = self.ticket(assignee_id=self.member.pk, priority="urgent")
        earlier = self.time(ticket_id=item["id"], task_id=None)
        converted = self.ticket_action(item, "create_task")
        retried = self.ticket_action(item, "create_task")
        self.assertEqual(converted["task_id"], retried["task_id"])
        self.assertEqual(Task.objects.get(pk=converted["task_id"]).assignee_id, self.member.pk)
        self.assertEqual(Task.objects.get(pk=converted["task_id"]).priority, "high")
        task = self.call("get", f"tasks/{converted['task_id']}/")
        self.assertEqual(task["helpdesk_ticket_id"], item["id"])
        retained = self.call("patch", f"timesheets/{earlier['id']}/", {"description": "Work before task creation", "expected_version": earlier["version"]})
        self.assertIsNone(retained["task_id"])
        self.call("patch", f"helpdesk/{item['id']}/", {"project_id": self.project2.pk, "expected_version": converted["version"]}, 409)
        self.call("patch", f"tasks/{converted['task_id']}/", {"project_id": self.project2.pk}, 409)
        self.assertEqual(Activity.objects.filter(summary__startswith="Create task:").count(), 1)

    def test_ticket_versions_scoped_links_and_archived_source_retention(self):
        item = self.ticket()
        for invalid in (None, [], {}, True):
            self.ticket_action(item, invalid, 400)
        changed = self.call("patch", f"helpdesk/{item['id']}/", {"title": "Latest title", "expected_version": item["version"]})
        self.ticket_action(item, "start", 409)
        self.contact.is_active = False; self.contact.save()
        self.call("patch", f"helpdesk/{item['id']}/", {"description": "More context", "contact_id": self.contact.pk, "expected_version": changed["version"]})
        self.call("post", "helpdesk/", {"title": "New", "contact_id": self.contact.pk, "request_id": str(uuid4())}, 400)
        foreign = Project.objects.create(company=self.other, name="Private")
        self.call("post", "helpdesk/", {"title": "New", "project_id": foreign.pk, "request_id": str(uuid4())}, 404)
        response = self.client.get(f"/api/v1/companies/{self.other.pk}/erp/helpdesk/{item['id']}/")
        self.assertEqual(response.status_code, 404)

    def test_archived_ticket_is_readable_and_cannot_receive_new_notes_until_restored(self):
        item = self.ticket_action(self.ticket(), "archive")
        self.assertEqual(self.call("get", "helpdesk/")["count"], 0)
        self.assertEqual(self.call("get", "helpdesk/?active=false")["count"], 1)
        self.call("post", f"helpdesk/{item['id']}/messages/", {"body": "New note", "request_id": str(uuid4())}, 409)
        self.ticket_action(item, "start", 409)
        restored = self.ticket_action(item, "restore")
        self.ticket_action(restored, "start")

    def test_ticket_filters_due_date_and_approved_support_minutes(self):
        item = self.ticket_action(self.ticket(due_date=(timezone.localdate() - timedelta(days=1)).isoformat(), assignee_id=self.owner.pk), "create_task")
        entry = self.time(ticket_id=item["id"], task_id=item["task_id"], minutes=90)
        self.time_action(self.time_action(entry, "submit"), "approve")
        self.assertEqual(self.call("get", f"helpdesk/{item['id']}/")["approved_minutes"], 90)
        self.assertEqual(self.call("get", "helpdesk/?mine=true&overdue=true&q=HD")["count"], 1)
        self.ticket_action(item, "resolve", resolution="Fixed")
        self.assertEqual(self.call("get", "helpdesk/?overdue=true")["count"], 0)

    def test_service_records_are_read_only_in_admin(self):
        for model in (Department, Employee, HelpdeskTicket, TicketMessage, TimesheetEntry):
            handler = admin.site._registry[model]
            self.assertFalse(handler.has_add_permission(None))
            self.assertFalse(handler.has_change_permission(None))
            self.assertFalse(handler.has_delete_permission(None))
