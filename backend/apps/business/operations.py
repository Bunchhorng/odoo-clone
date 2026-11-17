"""Company-locked service workflows. Call writers inside transaction.atomic()."""
import hashlib
import json
from uuid import UUID, uuid4

from django.db.models import Sum
from django.utils import timezone

from apps.companies.access import membership_for
from apps.companies.models import Company, CompanyMembership
from apps.companies.permission_audit import PermissionImpact, permission_enforced
from apps.core.api import APIError, text_field
from .models import Contact, Employee, HelpdeskTicket, Project, Task, TicketMessage, TimesheetEntry
from .services import check_version, date_value, next_number, positive_id, record_activity, scoped

TIME_FIELDS = {"employee_id", "project_id", "task_id", "ticket_id", "date", "minutes", "description"}
TICKET_FIELDS = {"title", "description", "contact_id", "project_id", "assignee_id", "priority", "due_date"}
MANAGERS = ("owner", "admin")


def access(user, company_id, *, manager=False):
    membership_for(user, company_id)
    if not Company.objects.select_for_update().filter(pk=company_id).exists():
        raise APIError("Company not found.", 404)
    actor = membership_for(user, company_id)
    if manager and actor.role not in MANAGERS:
        raise APIError("An owner or administrator is required for this action.", 403)
    return actor


def request_uuid(data):
    try:
        return UUID(str(data.get("request_id", "")))
    except (ValueError, AttributeError):
        raise APIError("Send a UUID request_id to protect submission retries.") from None


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def related(model, company_id, value, previous=None, *, optional=True):
    if optional and value in (None, ""):
        return None
    item = scoped(model, company_id, value)
    if item.pk != previous and not item.is_active:
        raise APIError("Choose an active related record.")
    return item


def assigned_user(company_id, value, previous=None):
    if value in (None, ""):
        return None
    value = positive_id(value)
    if value != previous and not CompanyMembership.objects.filter(company_id=company_id, user_id=value,
            is_active=True, user__is_active=True).exists():
        raise APIError("Choose an active teammate in this company.")
    return value


def save_ticket(user, company_id, data, actor, item=None):
    creating = item is None
    if not creating:
        check_version(item, data)
        if actor.role not in MANAGERS and (item.created_by_id != user.pk or item.status != "new" or not item.is_active):
            raise APIError("Only your own new, active tickets can be edited.", 403)
    token = request_uuid(data) if creating else None
    payload = {key: data[key] for key in TICKET_FIELDS if key in data}
    if creating:
        previous = HelpdeskTicket.objects.filter(request_id=token).first()
        if previous:
            if previous.company_id != company_id or previous.created_by_id != user.pk or previous.payload_digest != digest(payload):
                raise APIError("This ticket request was already used with different details.", 409)
            return previous, False
    item = item or HelpdeskTicket(company_id=company_id, created_by=user, request_id=token, payload_digest=digest(payload))
    for key in ("title", "description"):
        if key in data or (creating and key == "title"):
            setattr(item, key, text_field(data, key, maximum=200 if key == "title" else 10000, required=key == "title"))
    for key, model in (("contact", Contact), ("project", Project)):
        if key + "_id" in data:
            value = related(model, company_id, data[key + "_id"], getattr(item, key + "_id"))
            if key == "project" and not creating and (item.task_id or item.timesheets.exists()) and getattr(value, "pk", None) != item.project_id:
                raise APIError("A ticket with a task or time entries cannot change project.", 409)
            setattr(item, key, value)
    if "assignee_id" in data:
        assignee = assigned_user(company_id, data["assignee_id"], item.assignee_id)
        if actor.role not in MANAGERS and assignee != item.assignee_id:
            raise APIError("Only an owner or administrator can assign tickets.", 403)
        item.assignee_id = assignee
    if "priority" in data:
        if data["priority"] not in ("low", "normal", "high", "urgent"):
            raise APIError("Choose a valid ticket priority.")
        item.priority = data["priority"]
    if "due_date" in data:
        item.due_date = date_value(data["due_date"], "Due date", optional=True)
    if creating:
        item.number = next_number(company_id, "HD")
    else:
        item.version += 1
    item.full_clean()
    item.save()
    record_activity(user, company_id, "helpdesk", item, f"{'Created' if creating else 'Updated'} {item.number}: {item.title}")
    return item, True


def ticket_action(user, item, data):
    action = data.get("action")
    if not isinstance(action, str):
        raise APIError("Choose a valid ticket action.")
    if action == "create_task" and item.task_id:
        return item
    check_version(item, data)
    if action == "create_task":
        if not item.is_active or item.status in ("resolved", "cancelled"):
            raise APIError("Reopen and restore this ticket before creating a task.", 409)
        if not item.project_id or not item.project.is_active:
            raise APIError("Choose an active project on the ticket first.")
        item.task = Task.objects.create(company_id=item.company_id, project=item.project,
            title=f"{item.number}: {item.title}"[:200], notes=item.description,
            assignee_id=assigned_user(item.company_id, item.assignee_id), due_date=item.due_date,
            priority="high" if item.priority in ("high", "urgent") else item.priority)
    elif action in ("archive", "restore"):
        item.is_active = action == "restore"
    else:
        if not item.is_active:
            raise APIError("Restore the ticket before changing its status.", 409)
        if action in ("start", "wait", "resolve", "cancel") and item.status in ("resolved", "cancelled"):
            raise APIError("Reopen the ticket before changing its status.", 409)
        states = {"start": "in_progress", "wait": "waiting", "resolve": "resolved", "cancel": "cancelled", "reopen": "in_progress"}
        if action not in states:
            raise APIError("Choose start, wait, resolve, cancel, reopen, create_task, archive or restore.")
        if action == "reopen" and item.status not in ("resolved", "cancelled"):
            raise APIError("Only resolved or cancelled tickets can be reopened.", 409)
        if action == "resolve":
            item.resolution = text_field(data, "resolution", maximum=2000)
            item.resolved_at = timezone.now()
            TicketMessage.objects.create(ticket=item, request_id=uuid4(), body=item.resolution,
                kind="resolution", actor_email=user.email)
        elif action == "reopen":
            item.resolved_at = None
        item.status = states[action]
    item.version += 1
    item.save()
    summary = f"{action.replace('_', ' ').capitalize()}: {item.number}"
    if action == "resolve":
        summary += f" - {item.resolution}"
    record_activity(user, item.company_id, "helpdesk", item, summary)
    return item


def add_message(user, ticket, data):
    token, body = request_uuid(data), text_field(data, "body", maximum=2000)
    existing = TicketMessage.objects.filter(request_id=token).first()
    if existing:
        if existing.ticket_id != ticket.pk or existing.actor_email != user.email or existing.body != body:
            raise APIError("This note request was already used with different details.", 409)
        return existing, False
    if not ticket.is_active:
        raise APIError("Restore the ticket before adding a note.", 409)
    message = TicketMessage.objects.create(ticket=ticket, request_id=token, body=body, actor_email=user.email)
    record_activity(user, ticket.company_id, "helpdesk", ticket, f"Added an internal note to {ticket.number}")
    return message, True


def own_time(user, actor, item):
    if actor.role not in MANAGERS and item.employee.user_id != user.pk:
        raise APIError("You can change only your own time entries.", 403)


def time_values(data, item=None):
    result = {}
    for key in ("employee_id", "project_id", "task_id", "ticket_id"):
        value = data.get(key, getattr(item, key, None))
        result[key] = positive_id(value) if value is not None and value != "" else None
    result["date"] = date_value(data.get("date", item.date.isoformat() if item else None), "Work date")
    if result["date"] > timezone.localdate():
        raise APIError("Time entries cannot be future-dated.")
    minutes = data.get("minutes", item.minutes if item else None)
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= 1440:
        raise APIError("Minutes must be a whole number from 1 to 1440.")
    result["minutes"] = minutes
    result["description"] = text_field({"description": data.get("description", item.description if item else "")}, "description", maximum=300)
    return result


def save_time(user, company_id, data, actor, item=None, request=None):
    creating = item is None
    if item:
        own_time(user, actor, item)
        check_version(item, data)
        if item.status != "draft":
            raise APIError("Only draft time entries can be edited.", 409)
    values = time_values(data, item)
    token = request_uuid(data) if creating else None
    if creating:
        previous = TimesheetEntry.objects.filter(request_id=token).first()
        if previous:
            if previous.company_id != company_id or previous.creator_email != user.email or previous.payload_digest != digest(values):
                raise APIError("This time request was already used with different details.", 409)
            own_time(user, actor, previous)
            return previous, False
    employee = related(Employee, company_id, values["employee_id"], item.employee_id if item else None, optional=False)
    if actor.role not in MANAGERS and employee.user_id != user.pk:
        raise APIError("Choose your own linked employee record.", 403)
    project = related(Project, company_id, values["project_id"], item.project_id if item else None, optional=False)
    task = related(Task, company_id, values["task_id"], item.task_id if item else None)
    ticket = related(HelpdeskTicket, company_id, values["ticket_id"], item.ticket_id if item else None)
    task_impact = permission_enforced(request, company_id, lambda: (
        PermissionImpact("task_not_assigned")
        if task and actor.role not in MANAGERS and task.assignee_id != user.pk else None
    ))
    if task_impact:
        raise APIError("Choose a task assigned to you.", 403,
                       headers={"X-Permission-Code": task_impact.reason})
    if task and task.project_id != project.pk:
        raise APIError("The task must belong to the selected project.")
    if ticket:
        retained = item and item.ticket_id == ticket.pk and item.task_id == values["task_id"] and item.project_id == project.pk
        # A task can be created after time was logged. Preserve the earlier entry's
        # task selection while requiring new/changed links to use the current task.
        if ticket.project_id != project.pk or (ticket.task_id and (not task or task.pk != ticket.task_id) and not retained):
            raise APIError("Use the ticket's project and linked task when logging support time.")
    day = TimesheetEntry.objects.filter(company_id=company_id, employee=employee, date=values["date"]).exclude(status="voided")
    if item:
        day = day.exclude(pk=item.pk)
    if (day.aggregate(total=Sum("minutes"))["total"] or 0) + values["minutes"] > 1440:
        raise APIError("An employee cannot log more than 24 hours on one date.", 409)
    item = item or TimesheetEntry(company_id=company_id, request_id=token, payload_digest=digest(values), creator_email=user.email)
    for key, value in values.items():
        setattr(item, key, value)
    if not creating:
        item.version += 1
    item.full_clean()
    item.save()
    record_activity(user, company_id, "timesheets", item, f"{'Logged' if creating else 'Updated'} {item.minutes} minutes: {item.description}")
    return item, True


def time_action(user, actor, item, data, request=None):
    own_time(user, actor, item)
    check_version(item, data)
    action = data.get("action")
    transitions = {"submit": ("draft", "submitted"), "withdraw": ("submitted", "draft"),
                   "approve": ("submitted", "approved"), "reject": ("submitted", "draft"), "void": ("approved", "voided"),
                   "discard": ("draft", "voided")}
    if not isinstance(action, str) or action not in transitions:
        raise APIError("Choose submit, withdraw, approve, reject, void or discard.")
    self_approval = permission_enforced(request, item.company_id, lambda: (
        PermissionImpact("self_approval_not_allowed")
        if action == "approve" and item.employee.user_id == user.pk else None
    ), action=action)
    if self_approval:
        raise APIError(
            "You cannot approve your own time entry.", 403,
            headers={"X-Permission-Code": self_approval.reason},
        )
    if action in ("approve", "reject", "void") and actor.role not in MANAGERS:
        raise APIError("Only an owner or administrator can review time.", 403)
    previous, status = transitions[action]
    if item.status != previous:
        raise APIError(f"This action requires a {previous} time entry.", 409)
    if action in ("reject", "void", "discard"):
        item.review_note = text_field(data, "reason", maximum=500)
    elif action in ("submit", "withdraw"):
        item.review_note = ""
        item.reviewed_by, item.reviewed_at = "", None
    if action in ("approve", "reject", "void", "discard"):
        item.reviewed_by, item.reviewed_at = user.email, timezone.now()
    item.status = status
    item.version += 1
    item.save()
    record_activity(user, item.company_id, "timesheets", item,
        f"{action.capitalize()} time #{item.pk}: {item.minutes} minutes" + (f" - {item.review_note}" if item.review_note else ""))
    return item
