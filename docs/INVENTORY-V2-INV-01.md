# Inventory V2 — INV-01: warehouses and stock locations

Branch: `feature/inventory-warehouse-locations`. Scope: warehouse/location
configuration and compatible ledger endpoints only. Existing partial purchase
receipts and supplier returns were already implemented and remain unchanged.
Reservations, transfers and new partial-delivery behavior are not implemented.

## Repository findings and implementation

The existing ledger stores signed `StockMovement.quantity` values. Product stock,
dashboard low-stock counts and delivery checks sum those values. Purchase
receipts, order lines, returns and adjustment reversals already retain document
references and use company transactions/locks. Accounting posts invoices and
payments; it does not value stock. INV-01 leaves those calculations and contracts
in place.

`Warehouse` adds company ownership, name, unique normalized short code, protected
internal stock-location identity and active/archive state. `StockLocation` adds
company ownership, unique code, name, parent, active/archive state and types:
internal, supplier, customer, inventory adjustment and view/grouping. View
locations organize a hierarchy and cannot be used as movement endpoints.

Every movement has protected, non-null source/destination foreign keys and a
`location_inferred` flag. The original signed quantity stays authoritative;
**endpoints are descriptions of that same movement, not extra stock entries**.
The source/destination check prevents identical endpoints. Company, usage and
hierarchy invariants are checked by model/API validation under the company lock.
MySQL cannot express cross-table company/ancestor rules with ordinary CHECK
constraints; raw SQL is not an authorized write path.

## Migration and preservation

Three small migrations separate MySQL schema changes from the atomic data step:

1. `0007_warehouse_location_schema`: tables, initially nullable links, foreign keys,
   uniqueness/usage checks and company/location/product indexes.
2. `0008_assign_legacy_stock_locations`: create one default warehouse and four
   company-owned locations for every existing company, then assign endpoints to
   existing rows **in place**. It creates no stock movements and changes no
   original movement fields.
3. `0009_require_stock_locations`: make both endpoint links non-null after backfill.

| Existing movement | Source → destination |
| --- | --- |
| Positive purchase receipt | Supplier → default internal stock |
| Negative sales delivery | Default internal stock → customer |
| Positive manual adjustment | Inventory adjustment → default internal stock |
| Negative manual adjustment | Default internal stock → inventory adjustment |
| Supplier return / adjustment reversal | Reverse the original movement's endpoints |

All historical physical locations are **inferred**: the legacy ledger recorded no
warehouse, aisle or bin. They are assigned to the default warehouse without
pretending to recover a physical location. Zero-quantity originals and unusual
order signs are retained, logged and flagged as inferred; sign determines the
direction so balances are preserved. Inconsistent correction quantities, cyclic
correction references, one-sided endpoints and cross-company product/order/source
references stop the data migration for inspection. They are not silently repaired.

Applied to the current local MySQL database: **3 default warehouses, 12 locations,
8 existing movements assigned, 0 unlocated movements**. The migration reported
0 zero-quantity and 0 unusual-sign originals. Before/after SHA-256 fingerprints
match for every original movement field, all 3 existing invoices, and the existing
journal-entry/line data (both empty in this local baseline). IDs, quantities,
timestamps, request IDs, receipt/order/line/correction references and notes were
preserved exactly. Ignored evidence: `.local/inv01-before.txt` and
`.local/inv01-after.txt`.

For another environment, back up MySQL and stop writers before applying the three
migrations together. MySQL DDL is not transactional. A failed data step rolls back
its assignments/defaults but leaves the additive `0007` schema applied; inspect
the reported legacy rows and rerun `migrate`. Do not fake migrations, delete
movements or reset volumes to get past an error. The migration acceptance suite
tests failure/retry on a disposable MySQL database.

Reversing the data step is a no-op; reversing the schema removes the newly added
configuration/links. A rollback to `0006` therefore loses INV-01 configuration.
Use a verified database backup if that configuration must be recovered. Original
movement rows are not replaced by the forward or reverse data step.

## Posting and archive rules

Existing APIs continue to post to the company's default stock location. Receipts
use the supplier location, deliveries use the customer location, and adjustments
use the inventory adjustment location. Corrections reverse the original endpoints.
No warehouse/location parameter has been added to existing write payloads.
`StockMovement.save()` handles endpoint defaults for existing transactional writers
and the demo seed; bulk inserts must provide valid endpoints explicitly.

For new companies without inventory configuration, the first warehouse created
becomes the default. If stock is posted first, the existing operation creates a
default Main Warehouse and virtual locations within its transaction. GET requests
never create configuration. Additional warehouses/locations are configuration only
until an explicitly scoped routing/transfer milestone.

Default warehouse/location records cannot be archived or have their posting type
or parent changed. A warehouse stock location is an internal root and cannot be
reassigned. Additional warehouses can be archived/restored when they have no
stock history. Referenced location types and hierarchies with movement history
cannot be repurposed/reparented. Parents require compatible types, the same
company, no cycles and at most 32 levels. Active children require active ancestors;
archive children first. Foreign keys protect parents, warehouse roots and movement
endpoints. The UI and APIs never hard-delete inventory configuration.

## API

Base: `/api/v1/companies/{company_id}/erp/`. Existing session and CSRF handling
remain in force. Active members can read; owners/admins can write. Related IDs
must belong to the requested company. Cross-company lookups return 404.

| Endpoint | Methods | Behavior |
| --- | --- | --- |
| `warehouses/` | GET, POST | Paginated list / create with stock location |
| `warehouses/{id}/` | GET, PATCH, DELETE | Detail / edit / **archive**, never hard delete |
| `locations/` | GET, POST | Paginated list / create |
| `locations/{id}/` | GET, PATCH, DELETE | Detail / edit / **archive**, never hard delete |
| `stock/?location_id={id}` | GET | Existing movement list filtered by either endpoint |

List filters: `q`, `active=true|false|all`, `page`, `page_size` (1–100). Locations
also accept `usage`, `parent_id` (`none` for roots) and `warehouse_id` (subtree).
Warehouse fields: `name`, `code`, optional `stock_location_id`, `is_active`.
Location fields: `name`, `code`, `usage`, nullable `parent_id`, `is_active`.
Company/system keys are not client writable. Codes are unique within a company;
warehouse codes start with a letter and contain at most 16 ASCII letters, digits,
hyphens or underscores. PATCH `is_active=true` restores an eligible record.

Movement/receipt responses add source/destination IDs and codes plus
`location_inferred`. Existing response fields, route paths, quantity signs,
receipt/reversal retry semantics and business actions are retained.

## Vue workflow

Inventory navigation now includes **Warehouses** and **Locations** alongside
Products and Stock movements. New routes: `/inventory/warehouses` and
`/inventory/locations`. Shared list/form/modal/search/pagination primitives are
reused. Loading, error/retry, empty, read-only and dirty-form states are preserved.

Warehouse creation can create an internal location automatically or use an eligible
existing internal root. The location screen provides list and hierarchy views,
type/state/search filters, parent selection and movement links. The hierarchy
loads all matching rows through paginated requests rather than presenting one
page as a complete tree. Filtered-out parents are identified by their stored
parent labels. Indentation is bounded on mobile. The movement ledger shows its
source/destination and marks inferred historical assignments.

## Acceptance and delivery boundary

Acceptance covers configuration CRUD/archive, input/type/parent/depth validation,
company isolation, read-only roles, protected references, stock/receipt/delivery
compatibility, real schema upgrade, retry/rollback and historical zero/unusual
sign preservation. Results are recorded in
[testing/INV-01-VERIFICATION.md](testing/INV-01-VERIFICATION.md).

The broad parity row **IN-03** remains **Partial**: INV-01 is the warehouse/location
milestone, while transfers and reservations remain out of scope. No work on those
features or partial sales deliveries was started. Changes remain on the feature
branch for solo review; no commits or deployment were made automatically.

Technical reference: [Django 5.2 migration behavior on MySQL](https://docs.djangoproject.com/en/5.2/topics/migrations/#mysql).
