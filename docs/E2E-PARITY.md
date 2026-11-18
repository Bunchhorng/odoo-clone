# E2E testing and parity verification

Verification date: **2026-10-29, Asia/Bangkok**. This pass covers the current
working tree, including existing feature changes, on local Docker/MySQL and
headless Microsoft Edge. The original audit remains a historical record.

## Results

| Check | Result |
| --- | --- |
| Compose configuration and Python dependency consistency | Passed |
| Django system check and migration consistency | Passed |
| Backend API, migration and MySQL concurrency suite | 177 tests passed |
| Vue production build | Passed |
| Full desktop/mobile browser suite | 51 workflow groups passed |
| Uncaught JavaScript errors / Vue runtime warnings | 0 / 0 |
| Browser fixture cleanup | Passed; temporary accounts and companies removed |
| Markdown/CSV parity consistency | 74 matching capabilities; linked local files exist |
| Parity verifier regression suite | 7 tests passed |

The final browser run was `5cc683be473fd11f`, completed at **16:22:48** local time
in **251.9 seconds**, using Edge `156.0.4314.50`. Its JSON report records successful
cleanup. The initial 48-group baseline also passed before the three added checks.

Browser checks exercise authentication/recovery, company access and switching,
catalog transfers, CRM-linked sales, delivery/invoice/payment, partial purchase
receipts and supplier returns, stock correction history, financial postings and
reports, employee directories, reviewed project time and internal Helpdesk.
They include stale forms, retry IDs, member restrictions, company boundaries,
desktop layouts and 375px mobile layouts. [VERIFICATION.md](VERIFICATION.md)
contains the full workflow checklist.

Three added browser groups verify seven currency choices, persistence after reload,
company isolation, currency snapshots/locking after the first order, and member
restrictions in Settings and the API. These validate the existing FI-09 boundary;
foreign exchange support remains missing.

## Parity conclusion and traceability

The [Markdown checklist](ODOO-PARITY-MATRIX.md) and its
[CSV copy](ODOO-PARITY-MATRIX.csv) agree on **25 Implemented, 27 Partial,
22 Missing and 0 Defect** across 74 selected capabilities. Statuses describe the
narrow named capabilities and their stated boundaries. This pass does not promote
any application to full parity.

The 25 implemented claims have the following automated evidence. Each ID has
source/test references in the full matrix; a shared workflow can cover several IDs.

| Implemented IDs | Evidence exercised |
| --- | --- |
| PL-01 | Fourteen-app launcher search and routed application workflows in ERP, accounting and service browser flows |
| PL-03, PL-05, PL-07, PL-09 | Company access, role/last-owner, CSRF/session and shared throttle tests in accounts/companies/business suites; owner/member browser sessions |
| PL-04 | Company-switch and page-clamping regressions in `test_foundation.py` and `browser-foundation-flow.mjs` |
| CP-01, CP-04, CP-05 | Contact/product validation, catalog filtering/transfers and retained inactive relations in business/catalog/foundation API and browser suites |
| CR-02, CR-03 | Pipeline revenue/probability acceptance and CRM quotation links/counts in `tests.py`, `test_crm_sales.py` and `browser-crm-sales-flow.mjs` |
| SA-01, SA-02, SA-04 | Decimal quotation totals, dirty/stale draft guards and full delivery in business/foundation/concurrency and ERP/CRM browser suites |
| PU-01 | RFQ confirmation, partial/full receipt and vendor bill in purchase/inventory API and purchase/ERP browser flows |
| IN-01, IN-02 | Immutable stock history, filtered tracing, reversals, negative-stock protection and competing fulfillment in purchase/inventory/concurrency suites |
| FI-02, FI-03, FI-04, FI-05 | Displayed invoice guards, partial/full settlement, repeated payment UUIDs and single completion activities in business/foundation/concurrency and ERP browser suites |
| FN-01 | Balanced document/payment journals, cancellation reversals, posting locks and historical import in accounting/concurrency and accounting browser suites |
| PJ-01 | Project/task record and assignee tests in `tests.py`; project/task forms in `browser-erp-flow.mjs` |
| OP-01, OP-07 | Existing-stack startup/checks, additive/test-database migrations and malformed related-ID regressions. Fresh-volume startup was verified at the foundation milestone and was not repeated in this pass. |

Corrections remove stale statements about defective payment activity and
inactive-assignee edits, attach existing automated evidence to PL-01 and CR-02,
and refresh commercial/accounting/service coverage references in OP-05.

The fixed reference remains **Odoo 19.0 documentation**, with edition entitlements
left open. Selected official sources were rechecked on this date:

- [CRM quotation creation](https://www.odoo.com/documentation/19.0/applications/sales/crm/acquire_leads/send_quotes.html) supports the linked-opportunity comparison.
- [Replenishment](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/warehouses_storage/replenishment.html) includes suggested/generated orders beyond KERP's threshold alert.
- [Credit notes/refunds](https://www.odoo.com/documentation/19.0/applications/finance/accounting/customer_invoices/credit_notes.html) extend beyond unpaid cancellation journal reversals.
- [Departments](https://www.odoo.com/documentation/19.0/applications/hr/employees/departments.html) and [Timesheets](https://www.odoo.com/documentation/19.0/applications/services/timesheets.html) include hierarchy, timers and time billing beyond KERP's directory/manual time workflows.
- [Helpdesk channels](https://www.odoo.com/documentation/19.0/applications/services/helpdesk/overview/receiving_tickets.html) and [SLA policies](https://www.odoo.com/documentation/19.0/applications/services/helpdesk/overview/sla.html) remain outside the internal ticket implementation.

Some direct requests timed out; indexed official documentation supplied the text.
No Odoo server or licensed edition was available for executable differential
testing. This is documentation-based comparison plus KERP runtime verification,
not an Odoo parity percentage or production certification. Main remaining gaps
include partial sales delivery/invoicing, locations/valuation, credit notes/refunds,
bank reconciliation/opening entries, app roles, localization and release controls.

## Reproduce

Run from the repository root on Windows:

```powershell
docker compose up -d --wait --wait-timeout 300
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
node scripts/verify-browser.mjs
python scripts/verify-parity.py
python -m unittest discover -s scripts -p test_verify_parity.py
```

Browser execution requires host Node.js 22+, Edge and the local console email
backend. Parity verification uses Python 3.9+ with the standard library. The
existing GitHub workflow now runs parity consistency and its regression tests;
hosted execution remains unverified. Edge E2E remains a local Windows check.

The full browser report is `.local/auth-browser-results.json`; `--catalog-only`
writes `.local/catalog-browser-results.json`. Reports include run ID, scope,
timestamps, browser version, completed groups, runtime errors/warnings and cleanup
outcome. A new run writes `running`; success is recorded after cleanup, while
failures write `failed` with completed groups and an error. Interrupted runs can
remain `running` and must not count as passes. Failure screenshots/page diagnostics
include the failing run ID in `.local/browser-failure.json`; a later successful
run can leave those older diagnostics, distinguished by their run ID.

The parity script compares every CSV/Markdown field, validates IDs, statuses,
priorities, required cells, totals, evidence labels, reference labels and local
evidence-file paths. Implemented rows require an automated-test evidence label.
Its regression tests introduce mismatched acceptance text, duplicate IDs, stale
totals, missing files and unsupported labels. It checks record consistency and
file presence; API/browser suites provide the functional evidence.
