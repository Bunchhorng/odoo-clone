# Implementation queue from the documentation audit

Reviewed: **2026-11-11, Asia/Bangkok**. This queue consolidates work described in
the project report, parity matrix, roadmap and module guides. It is not a claim
that each documentation file represents an independent feature request; setup,
guides, audits and verification records are reference documents rather than work
items.

## Rules for this queue

1. Complete one milestone, including migration, API/UI, permissions, concurrency
   tests, browser evidence and documentation, before starting the next.
2. Preserve existing APIs and historical stock/accounting records unless an
   reviewed compatibility migration is required.
3. Do not promote a parity row until its stated acceptance condition passes.

## Current dependency chain

| Order | Milestone | Source documents | State | Exit condition |
| ---: | --- | --- | --- | --- |
| 1 | INV-02A: reservations, delivery operations, partial sale delivery and backorders | `INVENTORY-GAP-ANALYSIS.md`, `SALES-INVENTORY-PARTIAL-FULFILLMENT-PLAN.md`, `ODOO-PARITY-MATRIX.md` | Backend verified; Vue/E2E pending | Reservation/retry/concurrency, partial picking/backorder and browser evidence pass. |
| 2 | SA-02A: per-line progress and multiple/partial invoice allocations | `SALES-GAP-ANALYSIS.md`, `CRM-SALES.md`, `ACCOUNTING-INTEGRATION.md` | Backend verified; Vue/E2E pending | Two delivered batches create exactly two balanced invoices without excess or duplicate allocation, including browser evidence. |
| 3 | Transfers and customer returns | `INVENTORY-GAP-ANALYSIS.md`, `PURCHASE-INVENTORY.md` | Backend verified; Vue/E2E pending | Location balances conserve company stock; return approval, damage/restock decision, and history reconcile through the user interface. |
| 4 | Credit notes, refunds and payment reversals | `ACCOUNTING-INTEGRATION.md`, parity rows FI-06/FI-07 | Not started | Immutable reversal/credit workflows reconcile to stock returns and journals. |
| 5 | Pricing, discounts, product variants/UoM and tax policy | `CONTACTS-PRODUCTS.md`, `CRM-SALES.md`, parity CP-06–08/FI-08 | Not started | Decimal pricing rules, snapshots and backend authorization pass. |
| 6 | Accounting depth: manual/opening entries, reconciliation, valuation and localization | `ACCOUNTING-INTEGRATION.md`, parity FN-02–04/IN-06 | Not started | Approved accounting policy, reconciliation and traceable valuation acceptance examples pass. |
| 7 | Reporting, activities/audit, attachments and per-app roles | `PROJECT-STATUS-REPORT.md`, parity PL-06/RE-01–03 | Not started | Backend-enforced scope/retention/report acceptance tests pass. |
| 8 | Service-app depth and expansion apps | `SERVICE-APPLICATIONS.md`, `ROADMAP.md` | Not started | Each selected app has separately approved scope and proof. |
| 9 | Production release work | `SETUP.md`, `FOUNDATION.md`, `PROJECT-STATUS-REPORT.md` | Not started | Production settings/hosting, HTTPS, restore drill, monitoring, hosted CI and release validation pass. |

## Completed reference milestones

The foundation, catalog, CRM/Sales connection, purchase partial receipts,
accounting foundation, service applications and INV-01 warehouse/location
configuration have their own implementation and verification documents. They are
not reopened by this queue unless a regression or a dependency requires a scoped
change.

## Next action

Finish the Vue workflow and browser evidence for milestones 1--3 before starting
credit notes, refunds, or unrelated ERP modules. The focused Django verification
suite currently covers deliveries, invoices, purchase inventory, transfers, and
customer returns; legacy migration-history tests must use a freshly recreated
test database and must not be reused with `--keepdb`.
