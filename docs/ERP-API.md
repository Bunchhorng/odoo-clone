# Business API reference

Base: `/api/v1/companies/{company_id}/erp/`. Requests use the existing session and
CSRF scheme documented in [API.md](API.md). An active company membership is required
for every endpoint. Members may read; owners/admins may write. Superuser status
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
| `contacts` | name, organization, email, phone, address, country, is_customer, is_supplier, notes, is_active |
| `products` | name, sku, category_id (nullable), barcode, kind (goods/service), sale_price, cost_price, unit, reorder_level, notes, is_active |
| `product-categories` | name (100 characters, company-unique), is_active |
| `opportunities` | title, contact_id (nullable), stage, expected_revenue, probability, expected_date (nullable), notes, is_active |
| `projects` | name, contact_id (nullable), notes, is_active |
| `tasks` | title, project_id, assignee_id (nullable), stage, priority, due_date (nullable), notes, is_active |

Responses include `id`, the fields above, created_at, and updated_at. Products add
`stock_quantity` and `category_name`; opportunities/projects add `contact_name`; tasks add project_name
and assignee_name. Contact requires a name and at least one customer/supplier flag.
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

Lists accept `q` (number/contact), `kind`, and `status` (draft/confirmed/cancelled).

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

The server calculates subtotal, tax_total, total with Decimal and half-up line
rounding. Client totals are rejected. Numbering is sequential per company and
document type: SO00001, PO00001, INV00001, BILL00001. The document snapshots
customer details, product descriptions/types, prices, quantities, taxes, and currency.

Action body: `{"action": "confirm"}`. Allowed actions:

- `confirm`: draft → confirmed. Re-confirming a confirmed order is harmless.
- `cancel`: draft/undelivered confirmed → cancelled if there are no movements or invoice.
- `fulfill`: confirmed → full delivery/receipt, sets fulfilled_at. Goods create
  signed stock movements. Services do not affect stock. Repetition does not duplicate
  movements. All product quantities are checked together, including repeated product
  lines. Insufficient stock returns 409 and rolls back the entire delivery.
- `invoice`: confirmed → create or return its invoice/bill. Returns an invoice
  response with lines/payments. Only one invoice/bill is supported per order.

Confirmed/cancelled orders cannot be edited. Full invoicing may occur before
delivery; this version has no delivered-quantity billing policy.

## Invoices and bills

| Method/path | Purpose |
| --- | --- |
| GET `invoices/` | Filter by q, kind (customer/vendor), status |
| GET `invoices/{id}/` | Snapshot, lines, paid_amount, balance, payments |
| PATCH `invoices/{id}/` | Draft date, due_date (nullable), notes only |
| POST `invoices/{id}/actions/` | `{"action":"issue"}` or `{"action":"cancel"}` |
| POST `invoices/{id}/payments/` | Register manual payment |

Invoices originate from order actions. Status: draft → issued → paid. Zero-value
invoices become paid when issued. Cancellation is allowed only without payments;
a paid invoice cannot be cancelled. The cancelled invoice remains linked to its
order and cannot be replaced in this version. Due dates may not precede invoice dates.

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
PDF endpoint. Invoices do not create general-ledger entries.

## Inventory

- `GET stock/`: paginated movement ledger with product_name/SKU, signed quantity,
  order_number or Adjustment, reason, actor_email, and timestamp.
- `POST stock/`: `{"product_id": 2, "quantity": "10.000", "reason": "Opening stock"}`.
  An active goods product and nonzero signed quantity are required. Adjustments
  that would make stock negative return 409. Entries cannot be edited/deleted.

Products' on-hand quantity is the sum of all their movements. A single stock pool
is maintained per company. No warehouse, lot, reservation, or valuation subsystem
is implied by these endpoints.

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
