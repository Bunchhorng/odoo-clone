import csv
import io
import json

from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from apps.companies.access import membership_for
from apps.core.api import APIError, api, json_body
from .catalog_transfer import safe_cell
from .models import Activity, Employee, HelpdeskTicket, Project, Task, TimesheetEntry
from .operations import (MANAGERS, TICKET_FIELDS, TIME_FIELDS, access, add_message, save_ticket,
                         save_time, ticket_action, time_action)
from .services import date_value, scoped
from .views import page


def ticket_queryset(company_id):
    return HelpdeskTicket.objects.filter(company_id=company_id).select_related("contact", "project", "task", "assignee", "created_by")


def ticket_data(item, detail=False):
    data = {key: getattr(item, key) for key in ("id", "number", "title", "description", "contact_id", "project_id", "task_id", "assignee_id",
            "created_by_id", "priority", "status", "due_date", "resolution", "resolved_at", "version", "is_active", "created_at", "updated_at")}
    data.update(contact_name=item.contact.name if item.contact_id else "", project_name=item.project.name if item.project_id else "",
        task_title=item.task.title if item.task_id else "", assignee_name=(item.assignee.get_full_name() or item.assignee.email) if item.assignee_id else "Unassigned",
        created_by_name=item.created_by.get_full_name() or item.created_by.email,
        overdue=bool(item.due_date and item.due_date < timezone.localdate() and item.status not in ("resolved", "cancelled")))
    if detail:
        data["approved_minutes"] = item.timesheets.filter(status="approved").aggregate(total=Sum("minutes"))["total"] or 0
        data["activities"] = list(Activity.objects.filter(company_id=item.company_id, resource="helpdesk", record_id=item.pk)
            .values("id", "actor_email", "summary", "created_at")[:20])
    return data


@api(["GET", "POST"])
def tickets(request, company_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        queryset = ticket_queryset(company_id)
        active = request.GET.get("active", "true")
        if active not in ("true", "false", "all"):
            raise APIError("Active filter must be true, false or all.")
        if active != "all":
            queryset = queryset.filter(is_active=active == "true")
        status = request.GET.get("status", "")
        if status:
            if status not in ("new", "in_progress", "waiting", "resolved", "cancelled"):
                raise APIError("Choose a valid ticket status.")
            queryset = queryset.filter(status=status)
        if request.GET.get("project_id"):
            queryset = queryset.filter(project=scoped(Project, company_id, request.GET["project_id"]))
        if request.GET.get("mine") == "true":
            queryset = queryset.filter(Q(assignee=request.user) | Q(created_by=request.user))
        if request.GET.get("overdue") == "true":
            queryset = queryset.filter(due_date__lt=timezone.localdate()).exclude(status__in=("resolved", "cancelled"))
        if request.GET.get("q"):
            search = request.GET["q"][:200]
            queryset = queryset.filter(Q(number__icontains=search) | Q(title__icontains=search) | Q(contact__name__icontains=search))
        return page(request, queryset, ticket_data)
    with transaction.atomic():
        actor = access(request.user, company_id)
        item, created = save_ticket(request.user, company_id, json_body(request, TICKET_FIELDS | {"request_id"}), actor)
        return JsonResponse(ticket_data(ticket_queryset(company_id).get(pk=item.pk), True), status=201 if created else 200)


@api(["GET", "PATCH"])
def ticket_item(request, company_id, record_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        scoped(HelpdeskTicket, company_id, record_id)
        return JsonResponse(ticket_data(ticket_queryset(company_id).get(pk=record_id), True))
    with transaction.atomic():
        actor = access(request.user, company_id)
        item, _ = save_ticket(request.user, company_id, json_body(request, TICKET_FIELDS | {"expected_version"}), actor,
                              scoped(HelpdeskTicket, company_id, record_id))
        return JsonResponse(ticket_data(ticket_queryset(company_id).get(pk=item.pk), True))


@api(["POST"])
def ticket_actions(request, company_id, record_id):
    with transaction.atomic():
        access(request.user, company_id, manager=True)
        item = ticket_action(request.user, scoped(HelpdeskTicket, company_id, record_id),
                             json_body(request, {"action", "expected_version", "resolution"}))
        return JsonResponse(ticket_data(ticket_queryset(company_id).get(pk=item.pk), True))


def message_data(item):
    return {key: getattr(item, key) for key in ("id", "body", "kind", "actor_email", "created_at", "request_id")}


@api(["GET", "POST"])
def messages(request, company_id, record_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        return page(request, scoped(HelpdeskTicket, company_id, record_id).messages.all(), message_data)
    with transaction.atomic():
        access(request.user, company_id)
        item, created = add_message(request.user, scoped(HelpdeskTicket, company_id, record_id), json_body(request, {"body", "request_id"}))
        return JsonResponse(message_data(item), status=201 if created else 200)


def time_queryset(user, company_id, params):
    actor = membership_for(user, company_id)
    queryset = TimesheetEntry.objects.filter(company_id=company_id).select_related("employee", "project", "task", "ticket")
    if actor.role not in MANAGERS:
        queryset = queryset.filter(employee__user=user)
    for key, model in (("employee_id", Employee), ("project_id", Project), ("task_id", Task), ("ticket_id", HelpdeskTicket)):
        if params.get(key):
            queryset = queryset.filter(**{key: scoped(model, company_id, params[key]).pk})
    for key, suffix in (("date_from", "gte"), ("date_to", "lte")):
        if params.get(key):
            queryset = queryset.filter(**{f"date__{suffix}": date_value(params[key], key)})
    if params.get("date_from") and params.get("date_to") and params["date_from"] > params["date_to"]:
        raise APIError("Start date cannot follow end date.")
    if params.get("status"):
        if params["status"] not in ("draft", "submitted", "approved", "voided"):
            raise APIError("Choose a valid time status.")
        queryset = queryset.filter(status=params["status"])
    if params.get("q"):
        text = params["q"][:200]
        queryset = queryset.filter(Q(description__icontains=text) | Q(employee__name__icontains=text) | Q(project__name__icontains=text))
    return queryset.order_by("-date", "-id")


def time_data(item):
    return {**{key: getattr(item, key) for key in ("id", "employee_id", "project_id", "task_id", "ticket_id", "date", "minutes", "description", "status",
        "request_id", "creator_email", "review_note", "reviewed_by", "reviewed_at", "version", "created_at", "updated_at")},
        "employee_name": item.employee.name, "employee_user_id": item.employee.user_id, "project_name": item.project.name,
        "task_title": item.task.title if item.task_id else "", "ticket_number": item.ticket.number if item.ticket_id else ""}


@api(["GET", "POST"])
def timesheets(request, company_id):
    actor = membership_for(request.user, company_id)
    if request.method == "GET":
        queryset = time_queryset(request.user, company_id, request.GET)
        response = json.loads(page(request, queryset, time_data).content)
        response["summary"] = queryset.aggregate(
            total_minutes=Sum("minutes", filter=~Q(status="voided")), approved_minutes=Sum("minutes", filter=Q(status="approved")),
            submitted_minutes=Sum("minutes", filter=Q(status="submitted")))
        response["summary"] = {key: value or 0 for key, value in response["summary"].items()}
        response["can_log"] = actor.role in MANAGERS or Employee.objects.filter(company_id=company_id, user=request.user, is_active=True).exists()
        return JsonResponse(response)
    with transaction.atomic():
        actor = access(request.user, company_id)
        item, created = save_time(request.user, company_id, json_body(request, TIME_FIELDS | {"request_id"}), actor)
        return JsonResponse(time_data(time_queryset(request.user, company_id, {}).get(pk=item.pk)), status=201 if created else 200)


@api(["GET", "PATCH"])
def time_item(request, company_id, record_id):
    item = time_queryset(request.user, company_id, {}).filter(pk=record_id).first()
    if item is None:
        raise APIError("Time entry not found.", 404)
    if request.method == "GET":
        return JsonResponse(time_data(item))
    with transaction.atomic():
        actor = access(request.user, company_id)
        item, _ = save_time(request.user, company_id, json_body(request, TIME_FIELDS | {"expected_version"}), actor,
                            scoped(TimesheetEntry, company_id, record_id))
        return JsonResponse(time_data(time_queryset(request.user, company_id, {}).get(pk=item.pk)))


@api(["POST"])
def time_actions(request, company_id, record_id):
    with transaction.atomic():
        actor = access(request.user, company_id)
        item = time_queryset(request.user, company_id, {}).filter(pk=record_id).first()
        if item is None:
            raise APIError("Time entry not found.", 404)
        time_action(request.user, actor, item, json_body(request, {"action", "expected_version", "reason"}))
        return JsonResponse(time_data(item))


@api(["GET"])
def export_time(request, company_id):
    queryset = time_queryset(request.user, company_id, request.GET)
    if queryset.count() > 10000:
        raise APIError("Narrow the filters to export at most 10000 entries.")
    output = io.StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    fields = ("id", "employee_name", "project_name", "task_title", "ticket_number", "date", "minutes", "description", "status", "review_note")
    writer.writerow(fields)
    for item in queryset.iterator(chunk_size=250):
        row = time_data(item)
        writer.writerow([safe_cell(row[field]) for field in fields])
    response = HttpResponse("\ufeff" + output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="timesheets-{company_id}.csv"'
    response["X-Content-Type-Options"] = "nosniff"
    return response
