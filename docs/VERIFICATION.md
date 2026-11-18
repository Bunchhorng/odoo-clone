# Verification record

The [foundation follow-up](FOUNDATION.md) resolves the five findings in the original
[repository audit](REPOSITORY-AUDIT.md). The subsequent
[Contacts/Products phase](CONTACTS-PRODUCTS.md) adds the shared Vue components and
catalog workflows. This record describes current verification; the original audit's
55-test/14-group and foundation's 78-test/16-group figures remain historical snapshots.
The [CRM/Sales follow-up](CRM-SALES.md) adds linked quotations, version conflicts,
archived draft selections, completion retries and cancelled-invoice correction.
The [Purchase/Inventory phase](PURCHASE-INVENTORY.md) adds partial receipts,
supplier returns, stock correction history and movement filters.
The [Accounting/integration phase](ACCOUNTING-INTEGRATION.md) adds balanced
document journals, posting locks, financial reports and source-document tracing.
The [service application phase](SERVICE-APPLICATIONS.md) adds employee/department
directories, project time review and internal Helpdesk with task/time links.

## Sales/inventory partial fulfillment implementation

On **2026-11-15**, backend implementation added reservations, delivery operations,
partial deliveries with backorders, multiple invoice allocations, internal
transfers, and approved customer returns. The focused Django suite passed **24
tests** across delivery, partial-invoice, purchase-inventory, transfer, and return
coverage. It includes retry-safe invoice/transfer/return requests, partial
transfers, restockable and damaged return decisions, and over-return rejection.

This is backend evidence only. Vue workflows, browser/E2E evidence, and dedicated
concurrency coverage for transfers and customer returns are still required before
these milestones can be called fully verified. The legacy warehouse migration
tests intentionally traverse historical schemas and require a fresh disposable
test database; they are not compatible with reusing `test_kerp` via `--keepdb`.

Verified on **2026-10-29**, Asia/Bangkok, against the local Docker/MySQL stack.

## Automated checks

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
node scripts/verify-browser.mjs
python scripts/verify-parity.py
python -m unittest discover -s scripts -p test_verify_parity.py
```

- Django system check: passed, no issues.
- Migration consistency: passed, no uncommitted model changes.
- Backend suite: **177 tests passed** on an isolated MySQL test database.
- Vue production compilation: passed.
- Browser suite: **51 workflow groups passed**, no uncaught JavaScript errors or
  Vue runtime warnings. The earlier catalog phase also verified its focused subset.
- Parity records: **74 matching capability rows**, with referenced local files
  present and automated-test evidence attached to all Implemented rows; **7 verifier
  regression tests passed**. See [E2E-PARITY.md](E2E-PARITY.md) for traceability.
- The additive catalog migration passed on the existing application database and
  the freshly created test database. The foundation milestone separately verified
  startup with fresh Compose volumes, test database privileges and proxy health.
- The additive opportunity-link/document-version migration passed on the existing
  application database and the freshly created test database.
- The receipt/stock-history migration passed on the existing and test databases;
  a regression verifies legacy movements retain their quantities and gain correct
  line/receipt links, including repeated product lines.
- The additive accounting migration passed on the existing and fresh test databases;
  demo seeding posts all three issued documents and both payments exactly once.
- The additive service-app migration passed on the existing and fresh test databases.
- Git whitespace check: passed. `.env` remains untracked.

Backend coverage includes session/CSRF, role enforcement, company and related-ID
isolation, input validation, decimal rounding/snapshots, workflow transitions,
stock adjustments, purchase receipts/sales deliveries, duplicate fulfillment,
partial/full payments, payment retry IDs, demo idempotence, and company preferences.
It also verifies shared authentication throttles, single-use/expired reset tokens,
queued recovery mail/retries, password validation, session revocation, numeric ID
errors, pagination clamping, inactive relationships and duplicate payment activities.
Catalog coverage adds scoped role/type/category/stock filters, allowlisted stable
sorting, optional unique barcodes, category retention, bulk operations, CSV quoting,
size/header/row validation, duplicate warnings/errors, preview binding/expiry,
all-or-nothing import, and sequential/concurrent retry receipts.

Concurrent MySQL tests verify that two simultaneous deliveries cannot oversell,
two payments cannot exceed the remaining balance, a retried payment is recorded
once, and two owner demotions cannot remove the final owner.
Concurrent CSV confirmation records one batch, one receipt and one set of activity.
Concurrent edits of one draft admit one writer and reject the stale version.
Concurrent invoice creation produces one invoice and one completion activity.
CRM/Sales regressions also verify scoped opportunity links/counts, role limits,
stale document transitions, retained archived lines and unpaid invoice restoration.
Purchase/Inventory tests verify partial receipts, remaining quantities, services,
archived goods, over-receipt rejection, stock-limited supplier returns, replacement
receipts, adjustment retries/reversals, filtering and company/role boundaries.
Concurrent receipt retries and adjustments produce one entry; competing receipts,
supplier returns and adjustment reversals cannot exceed their respective limits.
Accounting tests cover exact invoice/bill/payment accounts, decimal balance checks,
zero-value documents, cancellation/reissue history, closed-date rollback,
forward-only owner locks, explicit historical import, period opening balances,
company/member isolation, filters and read-only ledger administration. Concurrent
invoice issue and historical import post each source once; concurrent payment
retries also create one invoice posting and one payment posting.
The final demo/ledger idempotence check was rerun after its actor metadata update.
Service tests cover work-directory account/department scope, unique employee codes,
member read/write restrictions, approved-time immutability, rejection/void history,
daily whole-minute limits, future dates, linked task/project/ticket validation,
request replay/conflicts, stale edits/reviews, archive retention, draft discard,
historical task selection after later ticket conversion, full resolution
history and filtered CSV. Member own-time privacy also applies to dashboard activity.
Concurrent time creation cannot exceed the daily cap; retries create one draft;
competing reviewers reject one stale decision; ticket conversion creates one task.

## Browser workflows

The Windows/Edge smoke test creates temporary ordinary accounts and isolated
companies, then removes only its own records in dependency order. It checks:

1. Protected route redirects, invalid credentials, login, session restoration/logout.
2. Company creation, ownership, company switching and persistence.
3. Team additions, active status changes, last-owner protection, member restrictions.
4. App launcher search and navigation to fourteen implemented applications.
5. Contact, product, opportunity, project, and task forms.
6. Opportunity/task stage changes persisted through the API.
7. Opening stock → quotation → confirmation → delivery → invoice → partial/full payment.
8. RFQ → purchase confirmation → receipt → vendor bill.
9. Print action invocation, live dashboard amounts, and payment history.
10. Mobile layouts at 375px, health failure/recovery, company data clearing, session expiry.
11. Contact role filters, phone search, table sorting and confirmed bulk archive/restore.
12. File input, CSV cell/error previews, quoted multiline import, and UTF-8 export/template blobs.
13. Product categories, leading-zero barcodes, category/type/stock filters and inactive retention.
14. Dirty dialog cancellation, clean Escape closure, Tab/Shift+Tab wrapping and mobile forms.
15. Read-only Contact/Product forms and hidden write/import/selection controls for members.
16. Account password change/recovery, token URL cleanup, single use and recovered sign-in.
17. Prefilled CRM quotations, no empty order on form open, links/counts in both apps.
18. Stale confirmation rejection, explicit reload and review before confirmation.
19. Unpaid invoice cancellation, return to Draft, correction and reissue.
20. Quotation notes and retained line edits with archived contacts/products.
21. Clearable CRM stage filters and linked quotation actions at 375px.
22. RFQ supplier costs, partial receipts, received/remaining quantities and receipt history.
23. Supplier return, reopened purchase quantities and replacement receipt.
24. Product/type/order/reference movement filters and navigation back to orders.
25. Adjustment retry and audited reversal of a mistaken count.
26. Receipt dialogs and movement tables at 375px; read-only member inspection.
27. Invoice issue entries, order billing summaries and source links in both directions.
28. Partial cash settlement entries and payment retry without duplicate postings.
29. Vendor bill cancellation retains the original journal and adds one reversal.
30. Historical incomplete-report notice, explicit import and safe import retry.
31. Balanced trial balance/balance sheet, account drill-down and UTF-8 report CSV.
32. Owner date-lock dialog and closed-date issue rejection preserving the draft.
33. Company-isolated journal/report reads and read-only member financial controls.
34. Financial reports fit 375px; wide trial-balance tables scroll internally.
35. Departments/Employees forms, normalized codes and existing Team account links.
36. Helpdesk creation, customer/project links, retry-safe task conversion and notes.
37. Ticket-prefilled time, submission, approval and reasoned voids with correct totals.
38. Stale time saves retain unsaved values until explicit Reload latest.
39. Resolve/reopen cycles retain full earlier resolution text and note history.
40. Employee/time/ticket layouts fit 375px and reject foreign-company links.
41. Members see/export only own time and cannot approve or edit employee records.
42. Members create support requests/notes without ticket assignment/status privileges.
43. Company currency choices, saved preferences after reload and company isolation.
44. First-order currency snapshots, disabled Settings changes and API conflict protection.
45. Read-only member Settings and API rejection of currency changes.

The suite validates browser print invocation; it does not certify a saved PDF,
legal invoice layout, accounting compliance, or external payment execution.
No external payment is performed.

Generated screenshots and results are in ignored `.local/`, including
`erp-apps-desktop.png`, `erp-crm-desktop.png`, `erp-invoice-desktop.png`,
`erp-dashboard-desktop.png`, `erp-dashboard-mobile.png`, and
`auth-browser-results.json`. The catalog phase adds `catalog-products-desktop.png`,
`catalog-product-form-mobile.png` and `catalog-contacts-mobile.png`. Regenerate them
with the command above. The focused `--catalog-only` option writes
`catalog-browser-results.json` and does not replace the full-suite record.
The CRM/Sales phase adds `crm-linked-quotations-mobile.png`.
Purchase/Inventory adds `purchase-receipt-mobile.png`, `inventory-movements-mobile.png`
and `inventory-receipt-ledger-desktop.png`. Accounting adds
`accounting-reports.png` and `accounting-mobile.png`; both layouts were inspected.

The E2E/parity pass adds run IDs, timestamps, explicit running/passed/failed status,
browser version, group counts, runtime errors/warnings and cleanup outcomes to the
JSON browser reports. Failure diagnostics include their run ID so an older failure
can be distinguished from a later successful run. The latest full-suite evidence
and implemented-capability traceability are in [E2E-PARITY.md](E2E-PARITY.md).

## Local review

The stack is running with Vue on port **5175** and Django on **8001** in this
workspace's existing `.env`. Fresh clones use the example ports unless changed.
Sign in at <http://localhost:5175/login> and select **KERP Demo** to explore the
separate sample company. Existing company records and account passwords were preserved.

This verifies the implemented core. Full Odoo parity is not claimed; see
[ODOO-COVERAGE.md](ODOO-COVERAGE.md) for the remaining work.

Service-app screenshots include `employees-mobile.png`, `timesheets-mobile.png`,
`helpdesk-mobile.png` and `helpdesk-desktop.png`; desktop and mobile layouts were
inspected. A text separator found during visual review was corrected, the build passed,
and all 48 browser groups were rerun successfully. The final 19 service API tests
were also rerun after adding draft discard and historical task-retention coverage.
