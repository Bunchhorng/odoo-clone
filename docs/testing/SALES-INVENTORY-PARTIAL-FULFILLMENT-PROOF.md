# Sales/inventory partial-fulfillment proof report

Audit date: **2026-11-11, Asia/Bangkok**. Requested scope: partial sales
deliveries, backorders, stock reservations, warehouse transfers, customer returns,
and multiple/partial customer invoices.

## 1. Feature information

| Item | Evidence-based finding |
| --- | --- |
| Feature name | Sales/inventory partial fulfillment and multi-invoice workflow |
| Original missing functionality | Per-line ordered/reserved/delivered/invoiced quantities; partial sale deliveries; backorders; reservations; transfers; customer returns; and more than one invoice per order. |
| Implemented behaviour in this audit | **None.** The preceding task produced an architecture plan only. It changed no Django model, migration, service, API, Vue component, route, test, or browser workflow. |
| Existing related behaviour | Full sales delivery writes one negative movement per goods line; purchase receipt supports partial quantities; a confirmed order can create one full-order invoice; invoice payment supports partial/full payment. |
| Remaining limitations | The complete requested scope remains unimplemented. `Invoice.order` is still one-to-one, sale fulfillment is still all-or-nothing, and stock on hand does not account for reservations. |

The authoritative implementation plan is
[SALES-INVENTORY-PARTIAL-FULFILLMENT-PLAN.md](../SALES-INVENTORY-PARTIAL-FULFILLMENT-PLAN.md).
It requires approval of its business-policy decisions before development begins.

## 2. Source evidence

### Changed files in the preceding task

| Path | Change | Feature implementation evidence |
| --- | --- | --- |
| `docs/SALES-INVENTORY-PARTIAL-FULFILLMENT-PLAN.md` | Added design, schema/API/UI proposal, migration sequence and acceptance tests. | Planning only; not executable feature code. |
| `docs/testing/SALES-INVENTORY-PARTIAL-FULFILLMENT-PROOF.md` | Added this audit record. | Verification documentation only. |

There are no new feature models, migrations, backend service functions, API
endpoints, Vue pages/components, permission checks, or automated tests. The
warehouse/location files visible in the working tree belong to the earlier INV-01
milestone and must not be attributed to this unimplemented feature.

### Existing implementation inspected

| Area | Current evidence | Why it does not satisfy the requested feature |
| --- | --- | --- |
| Models | `Order.fulfilled_at`, `OrderLine.quantity`, `StockMovement`, and one-to-one `Invoice.order` in `backend/apps/business/models.py`. | No delivery/backorder/reservation/invoice-line model or progress quantities exist. |
| Services | `fulfill_order()` and `invoice_order()` in `backend/apps/business/services.py`. | They perform one full delivery and create/reuse one full-order invoice. |
| APIs | `orders/{id}/actions/`, `invoices/`, and stock endpoints in `backend/apps/business/urls.py` and `views.py`. | No operation/reservation/transfer/customer-return/partial-invoice endpoints exist. |
| Vue | `OrdersView.vue`, `InvoicesView.vue`, `StockView.vue`. | UI has one Validate delivery action and one invoice link; no backorder or invoice-quantity flow. |
| Permissions | `membership_for()` plus backend `write_access()` used by business views. | Company and owner/admin controls exist, but no feature-specific operation permissions are implemented. |

## 3. Tests performed

No feature tests were run because no feature code was added. The following
documentation/audit commands were run:

```powershell
Get-Content docs\PROJECT-STATUS-REPORT.md
Get-Content docs\ODOO-PARITY-MATRIX.md
Get-Content docs\ROADMAP.md
Get-Content docs\VERIFICATION.md
Get-Content backend\apps\business\models.py
Get-Content backend\apps\business\services.py
Get-Content backend\apps\business\inventory.py
Get-Content backend\apps\business\views.py
Get-Content backend\apps\business\urls.py
Get-Content frontend\src\router\index.js
Get-Content frontend\src\views\OrdersView.vue
Get-Content frontend\src\views\InvoicesView.vue
git diff --check -- docs\SALES-INVENTORY-PARTIAL-FULFILLMENT-PLAN.md
```

`git diff --check` produced no whitespace errors for the planning document.
These commands provide source inspection and documentation validation only; they
are not evidence that the requested workflow works.

The project’s earlier evidence remains historical baseline evidence, not evidence
for this feature: INV-01 reports 192 backend tests, 18 Playwright tests and 51
browser workflow groups passed on 2026-10-30. Its scope is warehouse/location
configuration and compatible ledger endpoints, not reservations, transfers,
partial sales delivery, or multiple invoices.

No API request/response evidence, feature browser E2E scenario, screenshot,
permission/company-isolation test, concurrency/retry test, migration test, or
full regression result exists for this requested scope.

## 4. Business verification

No requested end-to-end workflow can be demonstrated as implemented.

| Proposed workflow | Expected when the planned feature is implemented | Actual result today |
| --- | --- | --- |
| Sell 10 units; deliver 4 | One completed delivery for 4; linked backorder for 6; on-hand falls by 4; reservation remains for 6. | The sale has only a full `fulfill` action; it attempts to deliver all 10 or fails for insufficient stock. |
| Deliver 4 then invoice 4 | Draft customer invoice contains 4; later delivery of 6 permits a separate invoice. | `Invoice.order` permits one full-order invoice only. |
| Transfer internal stock | Stock moves from source internal location to destination internal location without changing company total. | Warehouses/locations can be configured, but no transfer operation/API/UI exists. |
| Customer returns 2 | A reverse physical movement is linked to the delivery and returnable quantity is enforced; financial correction is separately controlled. | Only supplier return and manual-adjustment reversal flows exist. |

No screenshots were generated because no browser scenario for this feature exists
or was run.

## 5. Final status

**Classification: Not implemented.**

The requested functionality has no feature code or migration, no executable API
or user interface, and no feature-specific automated or browser proof. The plan
is ready for scoped approval, but planning does not meet the defined acceptance
scope. Unverified scenarios include every partial delivery, reservation, backorder,
transfer, customer return, multiple/partial-invoice, permission, company-isolation,
concurrency, retry, migration, accounting-posting, and browser workflow described
in the plan.

The parity matrix intentionally remains: SA-05 **Missing**, IN-03 **Partial**
(warehouse/location configuration only), and FI-01 **Partial** (one order-based
invoice only). No status has been promoted by this report.
