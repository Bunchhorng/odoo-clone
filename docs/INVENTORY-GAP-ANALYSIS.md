# Inventory gap analysis and staged implementation proposal

Audit date: **2026-11-11, Asia/Bangkok**. Scope: current working tree,
including the uncommitted INV-01 warehouse/location milestone. This is an audit
and implementation proposal, not evidence that the proposed features work.

## 1. Current inventory architecture

KERP uses a Django/MySQL append-only `StockMovement` ledger. Its signed
`quantity` is the current company stock authority: positive receipts/adjustments
increase stock, negative sales deliveries/returns decrease it. `StockMovement`
now stores non-null, protected source and destination `StockLocation` links. The
INV-01 migration inferred endpoints for legacy movements without creating a
second stock entry.

Existing business mutations execute in `transaction.atomic()` and the current
delivery path is guarded by the company lock. Company access is enforced by
`membership_for()` and mutations call backend `write_access()`. The frontend is a
Vue SPA that uses company-scoped ERP requests and contains product, movement,
warehouse and location views. Docker Compose provides MySQL, backend, frontend
and mailer; CI runs parity verification, fresh Compose startup, Django tests and
frontend checks.

## 2. Existing models and relationships

| Model / service | Current relationship or behaviour | Audit result |
| --- | --- | --- |
| `Product` | Company-scoped SKU/catalog with goods/service type, simple cost/sale price and reorder threshold. | Implemented narrow catalog; no tracking policy, supplier terms or valuation configuration. |
| `Order` / `OrderLine` | Sale/purchase documents; line has one ordered `quantity`; order has one `fulfilled_at`. | Full sale delivery only. Purchase supports partial receipt through movements. |
| `StockMovement` | Company/product/order/order-line/receipt links, immutable signed quantity, correction links and source/destination locations. | Physical ledger works within its present endpoints; it is not a reservation, picking, transfer or valuation document. |
| `Warehouse` / `StockLocation` | Company warehouse root; hierarchy of internal/supplier/customer/inventory/view locations, archive protection and movement endpoint validation. | Multiple warehouses and hierarchy configuration work. Extra warehouses are not yet routing/stock-operation targets. |
| `PurchaseReceipt` | Numbered, idempotent partial purchase receipts. | Implemented; it must remain compatible. |
| `Invoice` | `OneToOneField(Order)`, with its lines read from the order. | One full-order customer invoice/bill only; blocks multiple/partial invoices. |
| `accounting.py` | Balanced document/payment journals and reversal entries. Inventory has no costing layers and creates no valuation entries. | Preserve its immutable posting rules; defer valuation integration. |

## 3. Verified current capability versus requested scope

| Requested area | Actual current state | Classification |
| --- | --- | --- |
| Product/SKU/category/barcode/goods-service catalog | Present with company scoping, optional barcode text and category retention. | Partial |
| On-hand stock and movement history | Present as signed company-level product balance; movement filters and endpoints are present. | Implemented within current ledger scope |
| Stock adjustment and reversal retry safety | Present, including idempotent request IDs and reversal/return links. | Implemented within current scope |
| Full sales delivery/no oversell | Present; a full delivery creates all movements or fails. | Implemented within current scope |
| Partial purchase receipts/supplier returns | Present; received/remaining quantities work for purchases. | Partial overall purchasing depth |
| Multiple warehouses/location hierarchy | Present as configuration, with default posting root and archive/reference protections. | Partial |
| Per-warehouse/location quantity availability | Location endpoints can be listed and movements filtered, but no authoritative per-location quantity/availability API exists. | Missing |
| Reservations/available/incoming/outgoing/forecast | Absent. Current stock is on-hand only and does not subtract demand. | Missing |
| Partial sales delivery/picking/backorder | Absent. No picking document; `fulfilled_at` represents completion only. | Missing |
| Internal transfer/transit | Explicitly rejected by current location validation. | Missing |
| Customer returns | Absent. Supplier return exists but cannot serve as a customer-return workflow. | Missing |
| Lot, serial, expiry, scanning | No corresponding models or workflows. | Missing |
| Standard/AVCO/FIFO valuation | No valuation layers or inventory-accounting reconciliation. | Missing |
| Replenishment/RFQ generation | Only a low-stock threshold/dashboard count exists. | Missing |

The project reports and parity matrix correctly state that the broad warehouse,
transfer and reservation row is Partial only because INV-01 delivered warehouse
and location configuration. It must not be interpreted as transfer/reservation
support.

## 4. Architecture risks and dependencies

1. `stock_for(product)` sums every company movement, so it cannot answer stock at
   a warehouse/location or available stock after reservations.
2. A signed movement expresses a completed physical result. Using it to represent
   a future reservation would falsely alter on-hand stock and double-count a later
   delivery.
3. `Order.fulfilled_at` and `Invoice.order` one-to-one assumptions must be
   migrated before partial delivery and multiple invoicing can be correct.
4. The existing company lock protects no-oversell but becomes unnecessarily broad
   for multi-location operations. New code needs deterministic, product/location
   row locking without weakening current safety.
5. Historical movements have inferred locations. New allocation logic may use
   those endpoints for audit/history, but must not claim recovered bin-level facts.
6. Valuation depends on reliable physical operations, return policy, product
   costing policy and accounting methodology. It must follow—not precede—the
   delivery/transfer/return ledger.
7. Replenishment depends on a defined forecast calculation, vendor lead-time and
   purchase policy; it cannot be safely inferred from current `reorder_level`.

## 5. Odoo 19 reference and edition boundary

Odoo 19 documents reservation timing by operation type, delivery validation with
backorder creation, and invoicing policies based on ordered or delivered
quantities. It also documents internal transfers when storage locations are
enabled. KERP should reproduce the selected business rules in Django/Vue, not
copy Odoo source code, branding or proprietary assets.

The official edition material describes Community as the open-source core and
Enterprise as built on that core, but its user documentation is not a reliable
feature-by-feature edition entitlement table. This audit therefore makes no
unsupported Community/Enterprise availability claim. Enterprise-associated
extensions such as barcode/mobile, advanced routes, replenishment automation and
carrier/portal integration require a separate licensing/product decision.

References: [reservation methods](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/shipping_receiving/reservation_methods.html),
[invoicing policies](https://www.odoo.com/documentation/19.0/applications/sales/sales/invoicing/invoicing_policy.html),
[partial-delivery backorders](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/shipping_receiving/setup_configuration/multipack.html),
and [Odoo editions overview](https://www.odoo.com/documentation/19.0/administration.html).

## 6. Proposed database and API changes

The detailed first-milestone schema/API contract is in
[SALES-INVENTORY-PARTIAL-FULFILLMENT-PLAN.md](SALES-INVENTORY-PARTIAL-FULFILLMENT-PLAN.md).
The minimum durable design is:

| Phase | Models/data additions | API additions |
| --- | --- | --- |
| INV-02A reservations + deliveries | `StockOperation`, `StockOperationLine`, `StockReservation`; per-order-line ordered/reserved/delivered/invoiced progress; indexed immutable request IDs. | Order reservation and operation list/create/read/action endpoints; inventory availability/forecast read endpoints. |
| INV-02B transfers + customer returns | Extend operation types and endpoint validation for internal-to-internal and customer-to-internal movement. | Transfer/return creation, validation, cancellation and history endpoints. |
| INV-03 traceability | Lot, serial and allocation records with product/company constraints and expiry dates. | Lot/serial availability, assignment, traceability and expiry-filter endpoints. |
| INV-04 valuation | Cost policy, valuation layers and immutable movement-to-layer allocations. | Authorized valuation reports and reconciliation endpoints. |
| INV-05 replenishment | Reorder rules, supplier lead-time/preferences and idempotent proposal/RFQ links. | Forecast/replenishment proposal and draft-RFQ endpoints. |

Preserve current URLs and response fields where feasible. Add API fields rather
than changing their meaning. Existing `fulfill` may be a documented compatibility
shortcut only after the new delivery operation is fully tested; it must never map a
partial request onto existing full-fulfillment semantics silently.

## 7. Vue improvement plan

1. Extend the product inventory screen with on-hand, reserved, available,
   incoming, outgoing and forecast quantities, each labelled with one backend
   definition.
2. Add smart buttons and lists for deliveries, backorders, reservations, transfers
   and customer returns on sale/order and inventory surfaces.
3. Add one reusable operation form/list/detail view with status bar, source and
   destination, planned/reserved/done quantities, activity history and explicit
   Validate/Create Backorder/Cancel actions.
4. Keep warehouse/location configuration screens but add per-location balances
   after the backend quantity API is authoritative.
5. Add lots/serials, valuation and replenishment UI only in their later phases;
   do not render placeholder actions.

Every write action must be backed by a server capability check. Retain existing
loading/error/retry/dirty-form patterns and test 320px/table-scroll/keyboard
behaviour.

## 8. Implementation order and acceptance tests

### INV-02A — reservations and partial delivery/backorders (first milestone)

Implement only reservation, delivery operation, partial validation/backorder and
their sale-order quantity/invoiceability read model. Exclude transfers, returns,
lots/serials, valuation and replenishment.

Acceptance tests:

- With 10 available units, reserve 6 for sale A and only 4 for sale B; a further
  reservation waits/fails according to the documented policy.
- Two concurrent reservations never exceed 10. Replaying a request ID creates one
  reservation. Cancelling/releasing restores availability.
- Deliver 6 of an order for 10, creating a completed picking and one backorder for
  4. Across both pickings exactly 10 source-stock units are deducted.
- Repeat validation creates no duplicate movement; stale/concurrent validation
  cannot exceed outstanding demand.
- Foreign-company product/location/order IDs return the existing non-disclosing
  404 behaviour; members cannot mutate operations.
- Existing full delivery, adjustment/reversal, purchase receipt/return, invoice,
  accounting, browser and migration suites stay green.

### Subsequent milestones

INV-02B transfers/customer returns; INV-03 traceability; INV-04 valuation; then
INV-05 replenishment. Each requires its own approved policy, data migration,
permission matrix, backend/API/concurrency/browser tests, screenshots and proof
report before the next begins.

## Exact files expected in INV-02A

Modify `backend/apps/business/models.py`, `services.py`, `inventory.py`, `views.py`
or new focused operation views/services, `urls.py`, new migrations and targeted
backend/concurrency tests. Modify `OrdersView.vue`, `InvoicesView.vue` only for
invoiceability display, `StockView.vue`, new operation view/components, router,
types and browser tests. Update API/guide/parity/roadmap/verification documents
only after tests provide evidence.

No application code was changed by this analysis. Approval of the reservation
policy (at-confirmation default, partial reservation allowed versus waiting) and
the INV-02A boundary is required before implementation.
