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
| 1 | INV-02A: reservations, delivery operations, partial sale delivery and backorders | `INVENTORY-GAP-ANALYSIS.md`, `SALES-INVENTORY-PARTIAL-FULFILLMENT-PLAN.md`, `ODOO-PARITY-MATRIX.md` | In progress, unverified | Reservation/retry/concurrency, partial picking/backorder and full regression/browser evidence pass. |
| 2 | SA-02A: per-line progress and multiple/partial invoice allocations | `SALES-GAP-ANALYSIS.md`, `CRM-SALES.md`, `ACCOUNTING-INTEGRATION.md` | Blocked by 1 | Two delivered batches can create exactly two balanced invoices without excess or duplicate allocation. |
| 3 | Transfers and customer returns | `INVENTORY-GAP-ANALYSIS.md`, `PURCHASE-INVENTORY.md` | Not started | Location balances conserve company stock; returns reconcile physical/history rules. |
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

Continue milestone 1 only. Its first task is to repair/recreate the disposable
`test_kerp` test database left incomplete by an interrupted test runner, add
focused reservation tests, and prove the reservation API before adding any
partial-delivery/backorder or Sales invoice code.
