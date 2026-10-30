# Employees, Timesheets and Helpdesk

This phase adds three working applications to the existing commercial and
accounting modules. It is the selected next group of remaining Odoo-style apps,
not completion of every remaining application family. The Apps launcher now has
fourteen routed applications.

## Set up the work directory

1. An owner/admin opens **Employees → Departments**, selects **New**, and saves a
   department.
2. Open **Employees → New**. Enter a name and employee code, with optional work
   email, work phone, job title and department.
3. Choose an existing **Team account** if this employee should log their own time.
   Add the account in Team first. An employee record does not create an account,
   change its role, invite anyone, or send email.
4. Employee codes normalize to uppercase and are unique within the company.
   Each Team account can link to one employee per company; unlinked employees are
   allowed. New account selections require an active company teammate.
5. Archive employees/departments when needed. Existing inactive relationships
   remain visible and can be retained on historical records. New assignments
   require active records.

This is a work directory visible to company members. It has no private home
addresses, compensation, identity documents, contracts or payroll fields.
Employee-account links cannot change after any time has been logged, preserving
ownership of historical entries. Other work-directory fields remain editable.

## Log, submit and review time

1. Open **Timesheets → Log time**. Choose an employee, work date, project, optional
   task/ticket, whole minutes, and a work description.
2. Members can choose only their own linked employee. Owners/admins can log for
   any active employee, including employees without an account.
3. Save the Draft, review it, then **Submit**. A submitted entry is locked for
   editing. **Withdraw** returns it to Draft. **Discard draft** requires a reason,
   retains the record as Voided and removes it from daily allowance/totals without
   needing approval.
4. An owner/admin can **Approve** or **Return for correction**. Returning requires
   a reason and makes the entry editable again. Resubmission clears the current
   review metadata; prior review events remain in activity history.
5. Approved entries cannot be edited. A manager can **Void** an incorrect approved
   entry with a reason, retaining its original date, duration, description and
   links. Log a new corrected entry if needed. Voided time is excluded from logged
   and approved totals and releases the corresponding daily allowance.

Work dates cannot be in the future. Each entry has 1–1440 whole minutes. An
employee's total across all non-voided entries on one date cannot exceed 1440
minutes, including concurrent submissions. There is no clock timer or overlap
detection; durations are explicitly recorded in minutes.

Tasks must belong to the selected project. Ticket time must use that ticket's
project and, for new/changed links, its linked task when present. If a task is
created after time was logged, earlier draft entries can retain their original
task selection when corrected. A task with time or a linked support
ticket cannot move to another project. A ticket with time or a task also retains
its project. Existing draft time can retain inactive relationships for historical
corrections, while new assignments require active records.

Project cards, task cards/forms/lists, employee cards and tickets link to filtered
timesheets. Filters cover project/task/ticket/employee, status, date range and
description/person/project search. Totals apply to all matching records, not just
the current page. CSV exports all matching entries, capped at 10000, with UTF-8
BOM, quoting and first-open spreadsheet formula protection.

Members can read, summarize and export only their own time. Owners/admins see
company-wide entries. The shared dashboard also hides other employees' time-entry
activity from members. Ticket details show the company's aggregate approved support
minutes, while individual time-entry access still follows the own-time rule.

Approval is role-based: owners/admins may approve any submitted entry, including
their own. A separate-reviewer policy, billing, cost rates and project profitability
are not implemented. Approved hours create no invoice or accounting entry.

## Manage support tickets

1. Any active member opens **Helpdesk → New ticket** and supplies a title, optional
   description, customer, project, priority and due date.
2. Members can edit only tickets they created while those tickets remain New and
   active. An owner/admin manages assignments and status; assignees are active
   Team accounts. Assignees do not need Employee records to receive a ticket.
3. Owners/admins can **Start work**, mark **Waiting**, **Resolve** with a required
   resolution, or **Cancel ticket**. Resolved/cancelled tickets must be **Reopened**
   before another status change. Archived tickets must first be restored.
4. **Add note** appends an internal note to an active ticket. Notes and full
   resolution messages remain in paginated history. Reopening does not erase the
   previous resolution. Recent activity separately shows the latest 20 events.
5. For an active open ticket with a project, **Create project task** creates one
   linked task. It copies the current title, description, assignee, due date and
   priority (Urgent becomes High for the task). Retries create no additional task.
6. The ticket links to its project/task and support time. The task links back to
   the ticket. These are linked records, not continuously synchronized copies:
   subsequent assignment, date or task-stage changes are managed in their own app.
7. Follow **Support time** and **Log time** to prefill the ticket's project/task.
   Approved support minutes appear on the ticket.

Helpdesk supports search, status, archived/all records, project, overdue and
created-by/assigned-to-me filters. Overdue means a past due date on an unresolved,
uncancelled ticket. All tickets and internal notes are visible to active company
members. No customer portal, email delivery, SLA automation or external messaging
is implied by this internal workflow.

## Permissions and reliability

| Capability | Member | Owner / administrator |
| --- | --- | --- |
| Work directory and departments | Read | Manage/archive/restore |
| Own time | Read, create draft, edit draft, submit, withdraw, discard draft, export | Same, for all employees |
| Other employees' individual time/activity | Hidden | Read/manage/export |
| Review time / void approved time | No | Yes |
| Read company tickets and internal notes | Yes | Yes |
| Create ticket / edit own New active ticket | Yes | Yes |
| Add internal note | Yes | Yes |
| Assign, resolve, reopen, cancel, archive tickets / create task | No | Yes |

All writes acquire the company lock and run transactionally. Entry/ticket edits
and state actions require the latest integer `expected_version`; stale requests
return 409 without overwriting newer values. The UI preserves an unsaved stale
form until an explicit Reload latest action.

Creation of tickets/time and addition of notes require a UUID `request_id`.
Matching retries return the same current record with status 200; new creation
returns 201. Reusing the request with different details returns 409. Ticket
creation compares the original supplied fields; time creation compares normalized
IDs, date, minutes and description. Keep the exact original payload for retries.
State-action retries with stale versions return 409; task conversion separately
returns its existing linked task without another write.

No delete endpoints are exposed. Business administration remains read-only in
Django Admin, including the new models. Migration `0006_service_operations` adds
tables/constraints without rewriting existing business records or automatically
turning Team members into employees. The demo command retains its existing
commercial sample data; create directory records to explore these new apps.

## Remaining application work

| Application family | Current next work |
| --- | --- |
| HR | Attendance, leave balances/approvals, recruitment, contracts and jurisdiction-specific payroll |
| Service delivery | Timers, billable hours, rates/profitability, planning and configurable approval rules |
| Helpdesk and collaboration | Knowledge base, appointments/calendar, SLAs, customer portal and email integration |
| Operations | Manufacturing/BOM/MRP, quality, maintenance, POS and hardware/offline workflows |
| Customer-facing | Website/eCommerce, subscriptions, recurring billing and customer self-service |
| Marketing | Consent-aware campaigns, events and external delivery integrations |
| Documents and customization | File access/versioning, signatures, spreadsheet/reporting and configurable fields/apps |

See the [API reference](ERP-API.md), [coverage checklist](ODOO-PARITY-MATRIX.md),
and [verification record](VERIFICATION.md). Service rules and tests live in
[operations.py](../backend/apps/business/operations.py),
[operations_views.py](../backend/apps/business/operations_views.py),
[test_operations.py](../backend/apps/business/test_operations.py),
[concurrency tests](../backend/apps/business/test_concurrency.py), and
[browser-service-operations-flow.mjs](../scripts/browser-service-operations-flow.mjs).
