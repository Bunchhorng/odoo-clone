# Business API reference

Base: `/api/v1/companies/{company_id}/erp/`. Requests use the existing session and
CSRF scheme documented in [API.md](API.md). An active company membership is required
for every endpoint. General business writes require owners/admins. Members may
manage their own draft/submitted time and create/comment on tickets as described
below. Accounting date locks require an owner. Superuser status
does not bypass company membership. The selected company in the session is only a
preference; the URL's company is checked independently.

## Shared conventions

- JSON bodies only, with explicit supported fields. Company IDs, calculated totals,
  and document statuses cannot be mass-assigned.
- Amounts are returned as decimal strings. Send decimal strings to avoid client
  float ambiguity. Money supports two decimals; quantities support three.
- List responses: `{"results": [...], "count": 12, "page": 1, "page_size": 25}`.
- Query parameters: `page` (positive), `page_size` (1–100), `q` (search where listed).
- Out-of-range pages are clamped to the last page (page 1 for no results). Clients
  use the returned page; company/filter changes reset the UI page.
- Errors use `{"error": "message"}` with 400/401/403/404/409/415 statuses.
- Related contacts/products/projects/assignees must belong to the same company.
- Writes use a company row lock and transaction, including stock/payment checks.
- No business DELETE endpoints are exposed; catalog records support archiving.

## Catalog resources

Each resource supports `GET/POST {resource}/` and `GET/PATCH {resource}/{id}/`.
Lists default to active records. Use `active=false` for archived or `active=all`
for both. `q` searches names/titles; contacts also search organization/email/phone and
products search SKU/barcode/category. Staged resources accept a `stage` filter. Tasks accept a
company-scoped `project_id` filter.

| Resource | Writable fields |
| --- | --- |
| `departments` | name (company-unique, 100 characters), is_active |
| `employees` | name, employee_code (uppercase/company-unique, 64 characters), work_email, work_phone, job_title, department_id (nullable), user_id (nullable active Team account), is_active |
| `contacts` | name, organization, email, phone, address, country, is_customer, is_supplier, notes, is_active |
| `products` | name, sku, category_id (nullable), barcode, kind (goods/service), sale_price, cost_price, unit, reorder_level, notes, is_active |
| `product-categories` | name (100 characters, company-unique), is_active |
| `opportunities` | title, contact_id (nullable), stage, expected_revenue, probability, expected_date (nullable), notes, is_active |
| `projects` | name, contact_id (nullable), notes, is_active |
| `tasks` | title, project_id, assignee_id (nullable), stage, priority, due_date (nullable), notes, is_active |

Responses include `id`, the fields above, created_at, and updated_at. Products add
`stock_quantity` and `category_name`; opportunities/projects add `contact_name`; tasks add project_name
and assignee_name, plus helpdesk_ticket_id/number when linked. Employees include
department_name and user_name; employee search includes code, work email, job
title and department, with a company-scoped department_id filter. Employee account
links freeze after time has been logged; task projects freeze after time/ticket
links. Contact requires a name and at least one customer/supplier flag.
Product requires name and company-unique SKU. Project requires name. Task requires
title and project_id. Opportunity requires title. Names/titles allow 200 characters;
SKU allows 64, notes 10000, address 2000, phone 50, unit 30.

Opportunity stages: new, qualified, proposition, won, lost. Won/lost normalize
probability to 100/0. Task stages: todo, in_progress, done. Task priority: low,
normal, high. An assignee must be an active user with active membership in the
company. Archived related records cannot be newly selected. Existing inactive
relations can be retained while editing other fields; company-owned relations still
undergo company checks. The UI displays historical inactive choices and sends changed
fields rather than resubmitting unchanged relationships.

Opportunity responses also include `quotation_count` (all linked quotations/orders,
including cancelled ones). `opportunity_id=<id>` filters opportunities by a
company-scoped ID; use `active=all` to follow an archived historical link.

### Contact/product filtering and sorting

Contacts accept `role=all|customer|supplier|both`. Products accept
`kind=all|goods|service`, `category_id=<id>|none` (empty means all), and
`stock=all|low|out`. Low means goods at/below reorder_level; out means goods at/below
zero. Services are excluded from low/out filters. Foreign category IDs return 404.

Catalog lists accept `ordering`, default `-id`; prefix `-` means descending. Every
sort includes an ID tiebreaker. Shared fields are `id`, `updated_at` and `name`
(`title` for staged resources). Contacts also permit organization/email/phone;
Products permit sku/sale_price/cost_price/stock_quantity/category__name/barcode.
Unsupported sort fields/filter values return 400.

An optional barcode is a text value up to 64 characters, company-unique under the
database collation. Multiple empty values are allowed and returned as `""`. Clear
with `""`. Category references follow the same company/active-retention rules as
other catalog relations. There is no category deletion endpoint.

### Bulk archive/restore

`POST contacts/bulk/` or `products/bulk/` accepts:

```json
{"ids": [1, 2], "action": "archive"}
```

Use `restore` to reactivate. Owners/admins only. Supply 1–100 positive IDs; duplicate
IDs collapse to one selection. A missing/foreign ID rejects the complete operation.
The transaction returns `{"selected": 2, "changed": 2}` and logs only changed rows.
Repeating the same state change produces no extra activity.

### CSV preview, import and export

These routes exist only for `contacts` and `products`. All GET exports require
membership; preview/import require owner/admin and CSRF.

| Method/path | Body / response |
| --- | --- |
| GET `{resource}/export/?<filters>` | UTF-8 BOM CSV attachment for all matching rows, up to 10000; same filters/sort as list; page/selection ignored |
| GET `{resource}/export/?template=true` | Header-only CSV with supported import columns |
| POST `{resource}/import/preview/` | `{"csv": "name\nExample\n"}`; returns headers, count, rows, can_import, token, expires_in |
| POST `{resource}/import/` | `{"csv": "name\nExample\n", "token": "<preview token>"}`; 201 `{"created": 1, "replayed": false}`, or 200 with replayed=true for the same confirmed request |

Preview rows contain row (logical CSV record number), name, original `values`,
`errors` and `warnings`. Invalid rows return can_import=false/token=null without
writing records. Structural/header/size errors return 400. Files are capped at 200
records/512 KiB. The signed preview lasts 600 seconds and binds file digest, company,
resource and account. A new preview is a separate import. The original CSV must be
sent unchanged at confirmation.

Import creates records only; it does not update/merge existing records. SKU/barcode
duplicates are errors; contact email duplicates warn and create another contact.
Product CSV uses `category` names instead of category_id; categories must already
exist and be active in this company. Other columns match editable fields. Required
columns are name and, for products, sku. Boolean text accepts true/false, yes/no,
1/0. Empty optional boolean/numeric/type/unit cells use model create defaults.

Confirmation revalidates under the company lock; conflicting current state returns
409 and asks for another preview. Row creation, activity and retry receipt commit
together or all roll back. No CSV source file/cells are stored. Receipts retain a
token digest, resource and count, and prevent concurrent/sequential retry duplication.

Exports omit IDs/calculated stock, quote every cell and prefix spreadsheet formula
starters with an apostrophe. That prefix remains literal on reimport; no automatic
unescaping occurs. Spreadsheet re-save behavior is outside this guarantee. See the
[user guide](CONTACTS-PRODUCTS.md) for CSV samples and spreadsheet caveats.

## Orders

| Method/path | Purpose |
| --- | --- |
| GET `orders/?kind=sale` | Sales quotations/orders; kind=purchase for RFQs/purchases |
| POST `orders/` | Create draft order |
| GET `orders/{id}/` | Header and lines |
| PATCH `orders/{id}/` | Edit draft fields/replace all lines |
| POST `orders/{id}/actions/` | Confirm, cancel, fulfill, or invoice |

Lists accept `q` (number/contact), `kind`, `status` (draft/confirmed/cancelled), and
`opportunity_id` (company-scoped opportunity).

```json
{
  "kind": "sale",
  "contact_id": 1,
  "date": "2026-10-28",
  "notes": "Delivery by agreement",
  "lines": [{"product_id": 2, "quantity": "3.000", "unit_price": "19.99", "tax_rate": "7.00"}]
}
```

`date`/notes are optional. A line may include a description; otherwise the product
name is copied. Price defaults to sales price for sales and cost for purchases.
There must be 1–100 active product lines. Contacts must have the customer/supplier
flag appropriate for the kind. Quantity must be positive, price nonnegative, and
tax percentage between 0 and 100. Unknown line fields are rejected.

Sales creation may include `opportunity_id` (nullable). It must refer to an active
opportunity in this company. The relationship is fixed after creation; purchase
orders cannot have it. Creation does not change the CRM stage. Order responses
include `opportunity_id`, `opportunity_title` and integer `version`.

Order and invoice PATCH requests and new actions must include `expected_version`
from their last response. Missing/invalid values return 400; a stale value returns
409 without applying the change. New clients must reload and review conflicts.
Completed order transitions and invoice-cancellation retries return their existing
result without another completion activity. See [CRM-SALES.md](CRM-SALES.md).

For draft-line replacement, an optional line `id` retains an existing line. The ID
must belong to the order and occur only once. Retained lines can keep an archived
product; new product selections require an active product. Unchanged archived
contacts can be retained and their saved document details are preserved.

The server calculates subtotal, tax_total, total with Decimal and half-up line
rounding. Client totals are rejected. Numbering is sequential per company and
document type: SO00001, PO00001, INV00001, BILL00001. The document snapshots
customer details, product descriptions/types, prices, quantities, taxes, and currency.

Action body: `{"action": "confirm", "expected_version": 1}`. Allowed actions:

- `confirm`: draft → confirmed. Re-confirming a confirmed order is harmless.
- `cancel`: draft/undelivered confirmed → cancelled if there are no movements or invoice.
- `fulfill`: confirmed → full sales delivery or remaining purchase receipt, sets fulfilled_at. Goods create
  signed stock movements. Services do not affect stock. Repetition does not duplicate
  movements. All product quantities are checked together, including repeated product
  lines. Insufficient stock returns 409 and rolls back the entire delivery.
- `invoice`: confirmed → create or return its invoice/bill. Returns an invoice
  response with lines/payments. Only one invoice/bill is supported per order.

Confirmed/cancelled orders cannot be edited. Full invoicing may occur before
delivery; this version has no delivered-quantity billing policy.

### Partial purchase receipts

`GET/POST orders/{id}/receipts/` is purchase-only. Creation requires a UUID
`request_id`, the current `expected_version`, optional `notes` (300 characters),
and optional `lines`: `[{"line_id": 12, "quantity": "2.000"}]`. Omit lines to receive
all remaining goods; an explicit list needs 1–100 unique goods lines from that
order. A line quantity must be positive and cannot exceed its remaining quantity.

New receipts return 201 with `receipt`, updated `order`, and `replayed=false`;
matching retries return 200/replayed=true without more stock or activity. Reusing
the UUID with changed order/notes/quantities returns 409. Purchase responses include
`receipt_status`, `has_stock_movements`, and per-line received/remaining quantities.
Service-only completion creates a receipt without stock movements. See
[PURCHASE-INVENTORY.md](PURCHASE-INVENTORY.md) for full examples and upgrade behavior.

## Invoices and bills

| Method/path | Purpose |
| --- | --- |
| GET `invoices/` | Filter by q, kind (customer/vendor), status |
| GET `invoices/{id}/` | Snapshot, lines, paid_amount, balance, payments |
| PATCH `invoices/{id}/` | Draft date, due_date (nullable), notes, expected_version |
| POST `invoices/{id}/actions/` | action = issue/cancel/restore, plus expected_version; cancel accepts optional reversal_date |
| POST `invoices/{id}/payments/` | Register manual payment |

Invoices originate from order actions. Status: draft → issued → paid. Zero-value
invoices become paid when issued. Cancellation is allowed only without payments;
a paid invoice cannot be cancelled. The cancelled invoice remains linked to its
order. An unpaid cancelled document can return to Draft with `restore`, retaining
its number and activity history for corrections and reissue. One invoice per order
remains the model. Due dates may not precede invoice dates. Invoice responses
include `version`; successful edits, transitions and new payments increment it.

```json
{
  "amount": "25.00",
  "date": "2026-10-28",
  "method": "bank",
  "reference": "Deposit",
  "request_id": "0a970142-5f8d-47b0-a39f-4a60b58a8ca6"
}
```

Payments require an issued invoice and a positive amount no greater than its
remaining balance. Method: bank/cash. Date defaults to the company's local current
date and cannot precede invoice date. A UUID request_id makes submission retries
idempotent; omit it only if you deliberately accept a new request ID on each call.
Reusing an ID with different details returns 409. Full payment changes status to
paid. A retried payment does not create another completion activity. The response
is the refreshed invoice. No external payment is executed.

Invoice lines come from its immutable confirmed order. Contact/address/currency
values are copied at document creation. Print/PDF is a browser view, not a backend
PDF endpoint. Issue and payments create balanced ledger entries atomically; cancellation adds a linked reversal. Detail responses include journal_entry_count and opportunity_id. Order detail includes invoice_summary (status, total, paid, balance, journal_entry_count).

## Accounting

See [posting rules and boundaries](ACCOUNTING-INTEGRATION.md). All routes require
active membership. Owners/admins can import; only owners can close dates.

| Method/path | Body / response |
| --- | --- |
| GET `accounting/settings/` | currency, fixed accounts (code/name/kind), locked_through, version, unposted_invoices, unposted_payments |
| PATCH `accounting/settings/` | locked_through (YYYY-MM-DD), expected_version; owner only, forward-only, no future date or missing postings in closing range |
| POST `accounting/sync/` | `{}`; transactionally import missing current issued/paid documents and payments; returns settings plus created count; retry creates zero |
| GET `accounting/entries/` | Paginated entries with source invoice/order/payment/reversal IDs, actor, timestamps and all account/debit/credit lines |
| GET `accounting/reports/` | Trial balance rows, period revenue/expenses/profit, end-date assets/liabilities/accumulated_earnings/balance_check, debit/credit totals and missing-posting counts |

Entries/reports accept inclusive `date_from` and `date_to`, default January 1 of
the end date's year through today. Start after end returns 400. Entry filters:
`account` (fixed chart code), `journal` (sales/purchases/bank/cash), company-scoped
`invoice_id`/`order_id`, `q` (journal/invoice/order reference or partner), and normal
pagination. Entries sort by descending posting date then ID. An account filter
retains both sides of matching entries. No direct entry/account write endpoints
are exposed. Reading an empty chart/report creates no records.

Report accounts contain code/name/kind, opening (debit minus credit before start),
period debit/credit, balance (signed closing), closing_debit and closing_credit.
Profit is period revenue less purchases expense; balance sheet uses all entries
through end, with accumulated earnings since inception. Reports use the company
currency. Purchases are expensed on bill issue; stock movements do not post values.

Invoice cancellation accepts `reversal_date` (default max(today, invoice date)).
It must be open and cannot precede the original posting. Zero-value documents have
an empty monetary entry. Reissuing an unpaid restored document posts a new entry;
originals/reversals remain immutable. Issuing a currently issued/paid posted
invoice again returns the existing state without a new posting or activity.
Closed-date posting returns 409 and rolls back its source transition/payment.
Historical import excludes drafts and previously cancelled unposted documents.

## Inventory

- `GET stock/`: paginated movement ledger with product_name/SKU, signed quantity,
  movement kind, receipt details/notes, order links, source return/reversal IDs,
  returnable_quantity, can_reverse, reason, actor_email, and timestamp. Filters:
  `q` (product/SKU/reference/reason/receipt notes), `kind` (all/adjustment/receipt/
  delivery/return/reversal), company-scoped `product_id`/`order_id`, `date_from` and
  `date_to` (inclusive Asia/Bangkok dates).
- `POST stock/`: `{"product_id": 2, "quantity": "10.000", "reason": "Opening stock"}`.
  An active goods product and nonzero signed quantity are required. Adjustments
  that would make stock negative return 409. Optional UUID `request_id` protects
  retries; omitting it creates a distinct adjustment each time.
- `POST stock/{id}/return/`: positive quantity, reason, and UUID request_id. Targets
  an original purchase receipt; enforces unreturned quantity and current stock.
  Reduces net received quantities and reopens the order for a replacement receipt.
- `POST stock/{id}/reverse/`: reason and UUID request_id. Reverses one original
  manual adjustment with a linked opposite entry, without making stock negative.
  A manual adjustment can be reversed only once.

Stock writes return 201 for creation or 200/replayed=true for matching retries,
with current `stock_quantity`. Changed details under a used UUID return 409.
Original entries remain immutable. Returns leave vendor bills/payments unchanged;
partial billing and credit notes are separate future workflows.

Products' on-hand quantity is the sum of all their movements. A single stock pool
is maintained per company. No warehouse, lot, reservation, or valuation subsystem
is implied by these endpoints.

## Employees, Timesheets and Helpdesk

See [service application rules](SERVICE-APPLICATIONS.md). Employee/Department CRUD
uses the catalog routes above and requires owner/admin for writes. These are
company-visible work-directory records; they contain no private HR/payroll fields.
An account can link to one employee per company. Adding an employee does not
create an account or change any company role.

| Method/path | Body / response |
| --- | --- |
| GET/POST `helpdesk/` | Paginated tickets / create with title, description, contact_id, project_id, assignee_id, priority, due_date, UUID request_id |
| GET/PATCH `helpdesk/{id}/` | Detail / fields above plus expected_version; creation request_id is immutable |
| POST `helpdesk/{id}/actions/` | action=start/wait/resolve/cancel/reopen/create_task/archive/restore, expected_version; resolve requires resolution (1-2000 characters) |
| GET/POST `helpdesk/{id}/messages/` | Paginated immutable notes/resolutions / body (1-2000 characters), UUID request_id |
| GET/POST `timesheets/` | Paginated time plus matching summary / employee_id, project_id, optional task_id/ticket_id, date, integer minutes, description, UUID request_id |
| GET/PATCH `timesheets/{id}/` | Visible entry / editable draft fields above plus expected_version (creation request_id immutable) |
| POST `timesheets/{id}/actions/` | action=submit/withdraw/approve/reject/void/discard, expected_version; reject/void/discard require reason (1-500 characters) |
| GET `timesheets/export/` | All matching authorized entries as UTF-8 CSV, maximum 10000 |

Tickets accept q (reference/title/customer), status, active=true/false/all,
project_id, mine=true (created by or assigned to caller), overdue=true and shared
pagination. Statuses are new/in_progress/waiting/resolved/cancelled; priorities are
low/normal/high/urgent. Details include linked names, version, approved_minutes,
latest resolution and the last 20 activity events. Paginated messages include
kind=note/resolution, actor_email, body and timestamps; full previous resolutions
are retained. Notes do not change a ticket's edit version.

All active members can read company tickets and add internal notes, create
unassigned tickets, and edit their own active New tickets. Owner/admin is required
for assignment and all status/task/archive actions. New relations require active
same-company records; unchanged inactive relations can be retained. Task conversion
returns its existing task on retry without another activity. Tickets with a task
or time cannot change project. No external email is sent.

Timesheets accept employee_id/project_id/task_id/ticket_id, status,
date_from/date_to (inclusive, optional), q and pagination. Statuses are
draft/submitted/approved/voided. Summary contains total_minutes (non-voided),
approved_minutes and submitted_minutes for all matching rows. can_log indicates
whether the caller can open a new-entry workflow. Members' list/detail/summary/CSV
reads include only their linked employee's records, including archived history;
foreign or unowned detail IDs return 404. Members can write only their own time.
Owners/admins can manage all company entries and review submitted time.

Minutes are integers 1-1440, with a company-locked non-voided daily total <=1440
per employee. Date cannot be future-dated; description is 1-300 characters. Task
must match project, and new/changed ticket links must match its project/task.
Earlier entries can retain their original task selection if the ticket task was
created later.
Owners of draft time can discard it with a reason, retaining it as Voided and
releasing its daily allowance. Approved entries are immutable; void requires a manager's reason and retains work
values/history. Time approval does not create accounting entries or invoices.
Dashboard activity applies the same own-time visibility to ordinary members.

Ticket/time/note creation requires UUID retry IDs; a matching retry returns 200
instead of 201. Conflicting reuse returns 409. All edits/actions use current
integer expected_version; stale writes fail atomically with 409. No direct status,
company, reviewer, creator or task-link mass assignment is accepted. These models
remain read-only in Django Admin.

## Preferences and dashboard

- `GET settings/`: currency (USD default) and currency_locked.
- `PATCH settings/`: `{"currency":"THB"}`. Supported: USD/THB/EUR/GBP/SGD/AUD/CAD.
  Currency cannot change once any order exists.
- `GET dashboard/`: live currency, contacts/products, open_opportunities,
  pipeline_value, sales_total, quotations, receivable/payable, low_stock,
  open_tasks/overdue_tasks, pipeline stage summaries, recent_orders, activities.

Dashboard values cover all dates. sales_total is confirmed sales order value;
receivables/payables are remaining balances of issued invoices/bills. Low stock
means active goods stock at or below its reorder threshold. Activity records are
read-only and limited to the company's latest twelve events on the dashboard.
