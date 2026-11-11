# Sales, inventory, and partial-invoice implementation plan

Plan date: **2026-11-11, Asia/Bangkok**. Scope: partial sales deliveries,
backorders, stock reservations, warehouse transfers, customer returns, and
multiple/partial customer invoices. This is an architecture and delivery plan,
not an implementation approval or a claim of complete Odoo parity.

## Decision requested before implementation

Use these agreed rules for the first commercial-fulfillment milestone:

1. A confirmed sale reserves available goods at its source location. Service lines
   do not reserve stock or create delivery operations.
2. Delivery is performed by explicit delivery documents. Validating a partial
   delivery creates a linked backorder for the undelivered remainder.
3. Customer invoices are created from eligible quantities. The default policy is
   **delivered quantities** for goods and **ordered quantities** for services.
   The policy is snapshotted on the sale line at confirmation.
4. An invoice is an immutable business document once issued. A later customer
   return/refund is handled by a future, explicit credit-note milestone; it does
   not edit or delete the original invoice.
5. Existing purchase receipt and supplier-return behaviour is preserved. Purchase
   partial billing, valuation, credit notes, and bank reconciliation are excluded.

The policy and scope decisions above should be confirmed before code changes.

## Existing architecture and verified baseline

KERP is a Django session API with a Vue 3 single-page frontend and MySQL. Every
ERP endpoint is nested below a company ID. `membership_for()` hides unavailable
companies with 404 and `write_access()` applies the current owner/admin write
rule. Mutating business views use `transaction.atomic()`; existing concurrency
tests run on MySQL with `select_for_update` support.

### Commercial flow today

| Area | Current implementation | Limitation relevant to this milestone |
| --- | --- | --- |
| Sales order | `Order` has draft/confirmed/cancelled states and a version. `OrderLine` snapshots product, quantity, price and tax. | It has only `fulfilled_at`; there are no ordered/reserved/delivered/invoiced quantities per line. |
| Delivery | `fulfill_order()` writes one negative `StockMovement` for every goods line and sets `fulfilled_at`. | No delivery document, partial quantity, source-location choice, backorder, return, or reservation exists. |
| Stock | `StockMovement` is an append-only signed ledger with validated source/destination locations. Current on-hand is the sum of movement quantities. | On-hand is not availability. It cannot subtract commitments from open sales. |
| Warehouses | INV-01 provides company warehouses, active location hierarchy and protected default posting endpoints. | Additional warehouses are configuration-only; transfer operations and routing are absent. |
| Invoicing | `Invoice.order` is a `OneToOneField`; invoice lines are rendered from order lines. `invoice_order()` copies full order totals. | One order can produce only one, full-order invoice; invoice quantities are not independent snapshots. |
| Accounting | Issuing an invoice creates an immutable, balanced journal entry. Cancellation creates a reversal and paid documents cannot be cancelled. | The journal source assumes one invoice per order but can already support an invoice-level source key. |
| UI | `OrdersView` exposes Confirm, Validate delivery, Create invoice and one invoice smart link. `InvoicesView` shows order-derived lines. | No delivery/backorder smart buttons, reservation state, quantity progress, invoice wizard, or invoice list per sale order. |

Existing regression protection includes stale-version rejection, idempotent order
actions, no-oversell concurrent full deliveries, retry-safe payment posting,
company isolation and immutable accounting reversals. The baseline report records
192 backend tests and 51 browser workflow groups passed on 2026-10-30; the
current lightweight checks passed on 2026-11-11.

## Odoo 19 reference criteria

Odoo’s documented model is a useful behavioural reference, not a source-code or
branding target. Odoo describes delivery orders generated from confirmed sales,
reservation methods (at confirmation, manually, or before a scheduled date),
partial validation with backorders, and invoice policies based on ordered or
delivered quantities. It also documents draft invoices becoming posted accounting
documents when confirmed.

| Selected behaviour | Odoo 19 reference | KERP target for this milestone |
| --- | --- | --- |
| Reservation | An operation type can reserve at confirmation, manually, or before the scheduled date. | Implement **at confirmation** only, with a later manual-release/re-reserve action; defer scheduled-date automation. |
| Partial delivery/backorder | Validating a partial delivery creates a backorder for the remaining quantity. | Create an explicit delivery and an explicit linked backorder delivery; never mutate the validated delivery. |
| Delivered-quantity invoicing | A delivery-based policy permits an invoice only after delivered quantity exists; later deliveries can create later invoices. | Compute `invoiceable = delivered - invoiced` per sale line and create one draft invoice for selected eligible quantities. |
| Ordered-quantity invoicing | Odoo supports invoicing ordered quantities. | Support ordered-quantity service lines in the same invoice wizard; goods remain delivered-quantity for this milestone. |
| Customer return | Odoo records a reverse stock flow and handles the financial refund separately. | Receive customer-return stock as an explicit reverse delivery; defer credit-note/refund to the accounting milestone. |
| Internal transfer | Odoo can apply reservations to internal transfers when storage locations are enabled. | Implement confirmed/validated transfer documents between internal locations, with no automatic route or replenishment logic. |

The selected behaviour belongs to the standard Sales, Inventory, and Accounting
domains. The official edition material describes Community as the open-source core
and Enterprise as built on that core, but the cited user documentation does not
provide a feature-by-feature Community/Enterprise entitlement table. Therefore,
this plan makes no edition entitlement claim. KERP should implement the documented
business behaviour independently; Enterprise-only extensions such as advanced
automation, barcode/mobile workflows, carrier integration, and portal flows stay
outside this milestone.

Official references: [reservation methods](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/shipping_receiving/reservation_methods.html),
[invoicing policies](https://www.odoo.com/documentation/19.0/applications/sales/sales/invoicing/invoicing_policy.html),
[partial-delivery backorders](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/shipping_receiving/setup_configuration/multipack.html),
[invoice workflow](https://www.odoo.com/documentation/19.0/applications/finance/accounting/customer_invoices.html), and
[Community/Enterprise overview](https://www.odoo.com/documentation/19.0/administration.html).

## Required domain model

Do not overload `StockMovement` as the workflow document. It remains the
append-only physical ledger. Add operational documents and immutable line
allocations that explain why a movement exists.

| Model | Essential fields and relationships | Rules |
| --- | --- | --- |
| `OrderLine` (extend) | `ordered_quantity` (rename database field only through a compatibility property, or retain `quantity`), `reserved_quantity`, `delivered_quantity`, `invoiced_quantity`, `invoice_policy`, `source_location`, confirmation snapshot fields | All progress values are derived/validated from allocations; no client can patch them. `quantity` remains in API responses during compatibility period. |
| `StockOperation` | company, number, type (`delivery`, `transfer`, `customer_return`), state (`draft`, `ready`, `done`, `cancelled`), source/destination location, sale order nullable, parent/backorder nullable, version, request ID/digest, actor/timestamps | A completed operation is immutable. `backorder_of` forms an acyclic chain. All linked records share company. |
| `StockOperationLine` | operation, order line nullable, product, description/unit snapshot, planned, reserved, done quantities, source/destination locations | Goods only. `0 <= done <= reserved <= planned`; any remaining quantity becomes a line in exactly one backorder when the operation is completed partially. |
| `StockReservation` | company, order line, product, location, operation line nullable, quantity, state (`active`, `consumed`, `released`), request ID | Active reservations reduce availability; consumed/released records remain auditable. Unique/idempotency constraint per request plus row-level locking. |
| `Invoice` (change) | Replace `OneToOneField(Order)` with nullable `ForeignKey(Order)` named `source_order`; keep a temporary `order_id` compatibility property/response. | One order has many invoices. An invoice still has one source order in this phase; cross-order consolidated invoicing is deferred. |
| `InvoiceLine` (new) | invoice, order_line nullable, product nullable, description/product/tax/unit snapshots, quantity, unit price, totals, source-operation-line nullable | Invoice content is frozen independently of later order edits, returns, or product changes. Aggregate per order line may not exceed its invoiceable quantity. |

Add indexes for `(company, state, type)`, `(order_line, state)`,
`(product, location, state)`, and links used for progress. Use `PROTECT` for
posted-document and stock-history relationships. Do not add a mutable `reserved`
number to `Product`; calculate it from active reservations under the same lock used
to create/consume/release them.

### Quantities and invariants

For each goods sale line:

```text
0 <= invoiced <= delivered <= ordered
0 <= reserved <= ordered - delivered
available(location, product) = on_hand(location, product) - active_reservations(location, product)
```

For service sale lines, delivery and reservation are zero; invoiceable quantity is
`ordered - invoiced` under the chosen ordered-quantity policy. A customer return
may only reference a validated delivery line and cannot exceed delivered minus
previously returned quantity. It creates a positive movement from Customer to
Internal; it does not decrement `invoiced_quantity` or rewrite journals.

## API plan and compatibility

Keep current read endpoints and fields during the migration. Do not repurpose
`POST orders/{id}/actions/ {action: fulfill}` to mean a partial delivery.
For one release it may remain a compatibility shortcut that creates, reserves and
validates a full default-location delivery when no operation exists; then deprecate
it in API documentation after client migration.

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `orders/{id}/` | GET | Add per-line ordered/reserved/delivered/invoiced/remaining fields, operation counts, invoice count/status and smart-button targets; retain legacy fields. |
| `orders/{id}/reservations/` | POST | Reserve available quantities at the selected internal location. Payload has version and UUID request ID; return shortages and the created/replayed reservation state. |
| `orders/{id}/operations/` | GET, POST | List delivery/backorder operations; create draft delivery from remaining/reserved lines. |
| `operations/{id}/` | GET, PATCH | Read/edit a draft only, with expected version. |
| `operations/{id}/actions/` | POST | `reserve`, `release`, `validate`, `cancel`; validate payload includes done quantities and a create-backorder decision. Idempotent request IDs are required for irreversible actions. |
| `operations/{id}/returns/` | POST | Create a draft customer-return operation constrained to delivered, unreturned quantities. |
| `transfers/` and `transfers/{id}/...` | GET, POST/PATCH | Same operational model restricted to active internal locations; inventory role required. |
| `orders/{id}/invoiceable/` | GET | Return invoiceable line quantities and policy decisions. |
| `orders/{id}/invoices/` | GET, POST | List related invoices; create a draft invoice for explicit, validated line quantities. |
| `invoices/{id}/` | GET | Return stored invoice lines, not current order lines. Retain `order_id` during compatibility period and add `source_order_id`. |

All writes must validate company ownership server-side using `scoped()` and must
not rely on Vue visibility. Reject stale document versions with 409. Use a UUID
request ID plus canonical payload digest for creation/validation actions; a replay
with the same request returns the original result and a changed payload returns
409.

## Concurrency, transactions, and migration safety

The existing code locks at company scope. That prevents overselling but will become
a throughput bottleneck and is too coarse for per-location availability. For this
milestone, lock a deterministic set of rows in one atomic transaction:

1. `Company` row for sequence allocation and company-wide invariants.
2. Target `Order` and its selected `OrderLine` rows in ascending primary-key order.
3. Selected `Product` and source `StockLocation` rows in ascending primary-key order.
4. Active reservations and relevant operation lines for those product/location
   pairs, using `select_for_update()`.

Recalculate on-hand and active reservations while locked, then insert immutable
reservation/movement/operation records and update the denormalized progress only
when necessary. Enforce database uniqueness for request IDs and source-document
idempotency keys; catch integrity conflicts and reread the original completed
operation before responding. Keep the accounting journal insertion inside the
invoice-issue transaction as it is today.

Migration sequence:

1. Add new tables and nullable foreign keys only.
2. Create `InvoiceLine` records for every existing invoice from its then-current
   order lines, with exact totals and snapshot data; verify aggregate totals.
3. Backfill existing sale movements into immutable completed delivery operations,
   with `location_inferred=True` where INV-01 inferred endpoints. Do not change a
   movement ID, quantity, timestamp, endpoint, return link, or correction link.
4. Backfill existing full invoices as one full invoice allocation per order line.
   Validate totals and journal links before enforcing constraints.
5. Add non-null/unique/check constraints after a migration verifier proves no
   orphan, over-delivered, over-invoiced, or cross-company record exists.

Take a verified MySQL backup and stop writers before the data migration. MySQL DDL
is not fully transactional; provide a forward repair/retry path, never delete
historical movements or posted journal entries to bypass a failed migration.

## Permission model

The current owner/admin/member model is insufficiently granular for this scope.
Until the core role milestone lands, use explicit backend capabilities derived from
membership role and document them in one policy function:

| Capability | Owner | Admin | Member |
| --- | ---: | ---: | ---: |
| Read orders, operations, reservations, invoices | Yes | Yes | Yes, company scope |
| Create/edit draft sale orders | Yes | Yes | No |
| Reserve/release/validate deliveries and transfers | Yes | Yes | No |
| Create customer return | Yes | Yes | No |
| Create/issue customer invoices | Yes | Yes | No |
| Cancel/reverse operations or invoices | Yes | Yes for draft/unposted operations; owner-only for financial reversal policy | No |

Company scope applies to every linked ID, including locations, operation lines,
source movements, invoice lines, and retry records. Record the actor and an
activity for each irreversible transition. A general activity/chatter subsystem is
out of scope, but this work must use the existing `Activity` mechanism and avoid
silently changing history.

## Vue implementation plan

Reuse `ERPStatusBar`, `ERPModal`, `ERPDataTable`, `ERPFormView`, `ERPKanbanView`,
`ERPChatter`, common loading/error/dirty-state handling, and the design tokens.

| Surface | Required change |
| --- | --- |
| Sales order form | Add quantity columns (ordered, reserved, delivered, invoiced, remaining); smart buttons for deliveries/backorders, reservations, returns, and invoices; show shortages and policy without client-side authority. |
| Delivery form/view | New `StockOperationView.vue`: status bar, line-level planned/reserved/done quantities, source/destination, validate dialog and explicit backorder choice, links to source sale and generated backorder. |
| Transfers | Reuse `StockOperationView` with transfer wording and internal-location selectors. Do not duplicate movement logic in the view. |
| Invoicing | Replace the single invoice link with a list/count. A Create Invoice dialog loads `invoiceable`, permits only server-eligible quantities and opens the resulting draft. Invoice detail renders immutable `InvoiceLine` data and source delivery links. |
| Inventory movement view | Add operation number/type, source and destination (already partly available), and links to delivery/transfer/return documents. |
| Accessibility/mobile | Preserve keyboard modal focus, visible error/retry state, 320px line tables with horizontal scroll, non-colour status labels and disabled/read-only controls. |

Do not add a new UI action unless its server capability check exists. Vue may hide
controls for members, but API permission tests are the authority.

## Files expected to change

Backend: `backend/apps/business/models.py`, `services.py`, `inventory.py`,
`views.py`, `inventory_views.py`, `urls.py`, `accounting.py`, new focused service
modules for operations/reservations and new migrations/tests. Depending on final
routing, add `operations_views.py` endpoints instead of growing `views.py` further.

Frontend: `frontend/src/views/OrdersView.vue`, `InvoicesView.vue`, `StockView.vue`,
new `StockOperationView.vue`, router registration, API/type declarations, shared
ERP components only where a generic capability is genuinely reusable, CSS tokens
and browser tests.

Documentation: `ERP-API.md`, `ERP-GUIDE.md`, `PURCHASE-INVENTORY.md`,
`ACCOUNTING-INTEGRATION.md`, `ODOO-PARITY-MATRIX.md/.csv`, `VERIFICATION.md`, and
this plan’s completion/decision log. No change should claim a completed capability
until its migration, backend, browser, and concurrency evidence exists.

## Milestones and acceptance criteria

### M1 — quantity ledger and reservation foundation

Add progress/allocation models and APIs, backfill history, and make confirmed sale
orders reserve stock at the default internal location. Acceptance: concurrent
reservations for the last units yield one success and one shortage; replay creates
one reservation; release makes stock available; cross-company/location IDs fail;
existing full-delivery tests still pass unchanged.

### M2 — partial deliveries and backorders

Add delivery documents, partial validation and immutable linked backorders.
Acceptance: a 10-unit order can ship 4, creates one `done` delivery and one
backorder for 6, reduces on-hand by 4 only, consumes 4 reservations, leaves/retries
the remaining allocation correctly, and prohibits a second validation or delivery
beyond the unfulfilled balance. Competing partial validations cannot deliver more
than 10.

### M3 — transfers and customer returns

Add internal transfers and customer-return operations using the same ledger.
Acceptance: transfer preserves company total but changes location balances;
invalid/non-internal source or destination is rejected; a return cannot exceed the
delivery remainder and creates a reverse physical movement without changing the
original delivery or issued invoice.

### M4 — multiple/partial invoices

Replace the invoice one-to-one relation with explicit invoice lines and allocations.
Acceptance: after deliveries of 4 and 6, two invoice drafts can be created for 4
and 6; each issued invoice balances independently; retry creates only one document
and one journal entry; aggregate invoice quantities never exceed eligible quantity;
existing invoices retain line totals and journal source links exactly.

### M5 — UI, regression, release evidence

Finish responsive views, API documentation, user walkthrough and parity rows.
Acceptance: owner/admin/member UI and API behaviour match the permission table;
browser flows cover split delivery/backorder, transfer, return and two invoices;
Docker migrations, full Django suite, frontend checks/build, browser suite and
parity verifier pass from the review branch.

## Test matrix

Add backend unit/API tests for quantities, location compatibility, version conflicts,
invalid payloads, company isolation, archive handling, operations state transitions,
and immutable histories. Add MySQL concurrency tests for competing reservations,
two partial validations, validate-vs-cancel/release, two invoice creations for the
same eligible quantity, and retry replay. Add migration-executor tests with legacy
full deliveries/invoices, returns, unusual signed movements and rollback/retry
fixtures. Add Playwright/Edge E2E coverage for owner/admin/member permissions,
partial delivery/backorder, shortages, transfer, customer return, partial invoices,
mobile layout and browser errors/warnings.

## Risks and explicit non-goals

The greatest implementation risks are changing a one-to-one invoice schema while
preserving issued financial history, double-counting quantities from a signed
ledger, and treating reservations as stock movements. Mitigate them with separate
operational/reservation records, immutable allocations, narrow locks, data-migration
fingerprints and staged constraints.

Excluded: purchase partial billing/three-way matching, inventory valuation and
cost layers, lots/serials, routes/replenishment, scheduled reservation, consolidated
invoices across orders, down payments, credit notes/refunds, payment reversal,
bank reconciliation, customer portal, barcode/mobile scanning, and generic role,
activity, audit, attachment, or module-registry infrastructure. Those are separate
milestones and must not be folded into this one.
