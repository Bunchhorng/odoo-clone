# Odoo parity matrix — audited repository

Audit date: **2026-10-28, Asia/Bangkok**. Read with [the repository audit](REPOSITORY-AUDIT.md) and [the user walkthrough](ERP-GUIDE.md).

The [foundation follow-up](FOUNDATION.md) resolved A-01 to A-05 and added authentication recovery/throttling, fresh-volume verification and CI configuration. The [Contacts/Products phase](CONTACTS-PRODUCTS.md) adds shared Vue components, catalog CSV transfers, filters/sorting, bulk actions, categories and barcode storage. Historical audit counts are preserved in the audit report.

The [Accounting/integration phase](ACCOUNTING-INTEGRATION.md) adds document-derived journal entries, financial reports, posting locks and source tracing.

The [service application phase](SERVICE-APPLICATIONS.md), verified 2026-10-29, adds Employees, Timesheets and Helpdesk while preserving the remaining application checklist.

The [E2E/parity verification pass](E2E-PARITY.md), dated 2026-10-29,
rechecks these statuses against the current API/browser evidence and adds a
repeatable Markdown/CSV consistency check. Original audit counts remain historical.

The [Inventory V2 INV-01 milestone](INVENTORY-V2-INV-01.md) adds warehouses and locations while keeping the compound transfer/reservation capability Partial.

## Comparison baseline

The comparison uses **Odoo 19.0 documented capabilities** and the official editions page as references. It is an inclusive planning checklist: it is **not** a claim that every row belongs to Community Edition. Enterprise-dependent apps need an edition decision before implementation. Odoo 19 is a fixed reference here, not a claim about the latest release. No Odoo instance, Enterprise account, license entitlement, or Odoo source checkout was available for executable differential testing.

KERP is Django + Vue + MySQL, not an Odoo module distribution. This matrix audits the **current working tree** beyond starter commit `7040f04`. Existing modified/untracked files were included. Source checks and runtime probes support KERP statuses; official documentation supports the comparison scope. This is not exhaustive coverage of every Odoo feature.

## Status and priority

| Status | Meaning |
| --- | --- |
| Implemented | The narrowly named capability exists and has relevant verification; the entire Odoo app is not thereby complete. |
| Partial | A usable subset exists, with the concrete limitation stated. |
| Missing | No corresponding application workflow/model/API was found in the inspected repository. |
| Defect | A currently exposed capability has a reproduced defect; see A-01 to A-05 in the audit. |

P1 = stabilize the commercial core or satisfy a release gate; P2 = deepen existing apps; P3 = additional app scope. Priorities are proposed sequencing, not effort estimates or incident severity. Audit finding severity is defined separately in the audit report.

**Selected checklist totals:** 74 rows: 25 Implemented, 28 Partial, 21 Missing, 0 Defect. These are capability counts, **not a parity percentage**. The six originally defective rows now have verified fixes; the historical audit records the original five findings.

A portable spreadsheet copy is [ODOO-PARITY-MATRIX.csv](ODOO-PARITY-MATRIX.csv). Each acceptance cell defines the present boundary or the next observable completion condition.

## Platform and access

| ID | Capability | Status | Repository evidence | Current boundary / next acceptance condition | Priority | Odoo reference |
| --- | --- | --- | --- | --- | --- | --- |
| PL-01 | App launcher and app switching | Implemented | [U1], [U8], [U9], [T6] | Fourteen routed apps, including Employees, Timesheets and Helpdesk; this does not implement module installation. | P2 | S0 |
| PL-02 | Search, list/card views, saved filters | Partial | [U2], [U7], [T10] | Shared catalog components, contact/product filters, server sorting and bulk archive/restore work; saved filters and grouping remain. | P2 | S1 |
| PL-03 | Company-scoped access checks | Implemented | [B1], [T1] | Active membership is checked per request; keep cross-company regression tests. | P1 | S2 |
| PL-04 | Company switch on paginated screens | Implemented | [U2], [U6], [T8], [T6] | Company/filter changes reset the page; server clamping and client page adoption cover smaller result sets. | P1 | S2 |
| PL-05 | Company membership roles | Implemented | [B2], [T2] | Owner/admin/member and last-owner rule work within the documented company scope. | P1 | S2 |
| PL-06 | Per-app roles and own-document rules | Partial | [B17], [T14] | Members manage only their own time and their own New ticket drafts; time review and ticket management require owner/admin. Configurable per-app access and broader own-document policies remain. | P1 | S2 |
| PL-07 | Session login, logout, and CSRF | Implemented | [B4], [T3] | Current email/password and cookie-session path is tested; not an identity-platform parity claim. | P1 | S2 |
| PL-08 | Invitations, recovery, MFA, SSO | Partial | [B4], [T9], [O5] | Password change and queued single-use recovery are implemented; invitations, MFA and SSO remain missing. External SMTP remains unverified. | P1 | S2 |
| PL-09 | Login throttling and abuse controls | Implemented | [B4], [T9], [O5] | MySQL-backed identity/peer limits return 429 and Retry-After; public ingress needs a trusted-proxy policy and tuning. | P1 | S2 |
| PL-10 | Configurable apps, fields, and translations | Missing | [U1], [R1] | Add an extension/configuration model and translation support if these are parity targets. | P3 | S0 |

## Contacts and products

| ID | Capability | Status | Repository evidence | Current boundary / next acceptance condition | Priority | Odoo reference |
| --- | --- | --- | --- | --- | --- | --- |
| CP-01 | Customer/supplier contact CRUD and archive | Implemented | [B3], [U2], [T4], [T10] | Contact CRUD, role/phone filters, sorting and confirmed page selection for bulk archive/restore work. | P2 | S1 |
| CP-02 | Contact hierarchy and linked history | Missing | [M1] | Add parent/child contacts, delivery/invoice addresses, deduplication, and linked-document history. | P2 | S1 |
| CP-03 | CSV/XLSX import and export | Partial | [B15], [U7], [T10] | Contacts/products have CSV templates, cell/error/warning previews, atomic create-only imports with safe retries, and filtered exports; XLSX and update/relational mapping remain. | P2 | S3 |
| CP-04 | Editing records with inactive relations | Implemented | [U2], [B3], [T8], [T6] | Retained inactive choices remain visible; changed-field payloads and scoped validation allow ordinary edits without granting new access. | P2 | S1 |
| CP-05 | SKU, goods/service, prices, and cost | Implemented | [M2], [B3], [T4] | Company-unique SKU and simple prices work; this is not a full product-management app. | P2 | S4 |
| CP-06 | Variants, categories, images, barcodes | Partial | [M2], [M10], [U7], [T10] | Company categories and optional unique barcode text are implemented with archived-category retention; variants, images and scanning remain. | P2 | S4 |
| CP-07 | Units of measure | Partial | [M2], [M3] | Current unit is a product string; add unit categories, conversions, and document unit snapshots. | P2 | S4 |
| CP-08 | Pricelists and discounts | Missing | [M2], [M3] | Add customer/currency/date-based pricing and tested discount/rounding policies. | P2 | S5 |

## CRM

| ID | Capability | Status | Repository evidence | Current boundary / next acceptance condition | Priority | Odoo reference |
| --- | --- | --- | --- | --- | --- | --- |
| CR-01 | Opportunity pipeline and stage changes | Partial | [M4], [U2], [T4] | Fixed five-stage board works; add configurable stages, teams, and stage rules. | P2 | S6 |
| CR-02 | Expected revenue and probability | Implemented | [M4], [B3], [T4] | Manual values and won/lost normalization work; predictive forecasting is outside this row. | P2 | S6 |
| CR-03 | Opportunity-to-quotation conversion | Implemented | [M3], [M4], [T11] | CRM opens a prefilled quotation; saved quotations have company-scoped links, counts and navigation both ways. Multiple quotations are supported; winning remains explicit. | P1 | S6 |
| CR-04 | Activities, meetings, and lead automation | Missing | [M4], [R2] | Add activity ownership/deadlines, scheduling, lead capture and assignment; choose integrations. | P2 | S6 |

## Sales and purchase

| ID | Capability | Status | Repository evidence | Current boundary / next acceptance condition | Priority | Odoo reference |
| --- | --- | --- | --- | --- | --- | --- |
| SA-01 | Quotation/RFQ drafts and decimal totals | Implemented | [B5], [M3], [T4] | Saved drafts and server Decimal totals work, with 1-100 lines and a manual line-tax percentage. | P1 | S5 |
| SA-02 | Confirming the document currently displayed | Implemented | [U3], [U6], [T11] | Dirty forms block confirmation; document versions reject stale saves/transitions and preserve edits until an explicit reload. | P1 | S5 |
| SA-03 | Confirmed snapshots and immutability | Partial | [B5], [M3], [T4] | Prices, party details and lines freeze; add seller/legal fields and unit snapshots for fuller document depth. | P1 | S5 |
| SA-04 | Confirmed order to full delivery | Implemented | [B6], [T5] | Full goods delivery and service completion work; partial delivery is a separate missing capability. | P1 | S5 |
| SA-05 | Partial deliveries, backorders, invoiced quantities | Missing | [M3], [B6], [M5] | Track ordered/delivered/invoiced quantities per line and permit multiple partial documents. A reviewed implementation plan exists; no feature code or acceptance evidence exists yet. | P1 | S5 |
| SA-06 | Sales/purchase cancellation and reversal | Partial | [B7] | Current cancellation stops before fulfillment/invoicing; add stock/accounting-safe reversal workflows. | P1 | S7 |
| SA-07 | Customer portal, quotation email/signature | Missing | [R1], [R2] | Add explicit portal authentication, document sharing, delivery tracking, and signature states. | P2 | S5 |
| PU-01 | RFQ to purchase, receipt, and vendor bill | Implemented | [B5], [B8], [T12] | RFQs confirm, receive goods in parts, and create full-order vendor bills; API/browser checks cover the workflow. | P1 | S4 |
| PU-02 | Vendor pricing, approvals, and tenders | Missing | [M2], [M3], [R2] | Add vendor-specific terms/prices, approval rules, and comparison workflows. | P2 | S4 |
| PU-03 | Partial receipts, vendor returns, matching | Partial | [M3], [T12] | Numbered partial receipts, per-line net quantities and supplier returns for replacement work; three-way matching, partial billing and return credits remain. | P1 | S4 |

## Inventory

| ID | Capability | Status | Repository evidence | Current boundary / next acceptance condition | Priority | Odoo reference |
| --- | --- | --- | --- | --- | --- | --- |
| IN-01 | Stock movement ledger and on-hand balance | Implemented | [M6], [T12] | Search/type/product/order/date filters trace immutable movements; retry-safe adjustments and linked reversals preserve stock history. Signed company balances are retained; movements now carry source/destination location links (INV-01). | P1 | S4 |
| IN-02 | No-negative-stock and concurrent deliveries | Implemented | [B1], [B6], [T5] | Current full-delivery rule is protected by a company lock; it is KERP's policy, not universal Odoo configuration parity. | P1 | S4 |
| IN-03 | Warehouses, locations, transfers, reservations | Partial | [M13], [B18], [U10], [T15] | Company-scoped reservation, partial delivery/backorder, and internal transfer APIs now write auditable stock records. Customer return approval can restock or retain damaged goods outside stock. Vue workflow and browser evidence remain pending. | P1 | S4 |
| IN-04 | Lots, serials, expiry, and scanning | Missing | [M2], [M6] | Add traceable receipt/delivery quantities, unique serial rules, and barcode workflows. | P2 | S8 |
| IN-05 | Replenishment rules | Partial | [M2], [B10] | A threshold and dashboard count exist; add min/max, routes, and suggested/automatic orders. | P2 | S9 |
| IN-06 | Inventory costing and valuation | Missing | [M6], [M2] | A product cost is not valuation; add cost layers, accounting links, and reconciliation. | P1 | S4 |

## Invoicing, payments, and accounting

| ID | Capability | Status | Repository evidence | Current boundary / next acceptance condition | Priority | Odoo reference |
| --- | --- | --- | --- | --- | --- | --- |
| FI-01 | Customer invoices and vendor bills | Partial | [M5], [B8] | Order-based creation supports delivered partial allocations and immutable invoice-line snapshots. Standalone documents and Vue/browser workflow evidence remain pending. | P1 | S10 |
| FI-02 | Issuing the invoice currently displayed | Implemented | [U4], [U6], [T6] | Dirty invoices/bills block issue until Save or Discard; saved dates, due dates and notes are retained. | P1 | S10 |
| FI-03 | Manual partial/full payment recording | Implemented | [B11], [T4] | Bank/cash records and remaining-balance checks work; no external payment is executed. | P1 | S10 |
| FI-04 | Payment retry without duplicate financial rows | Implemented | [B11], [T5] | UUID retries preserve one payment even concurrently; completion-activity correctness is verified separately in FI-05. | P1 | S10 |
| FI-05 | Payment retry without duplicate activity | Implemented | [B11], [B12], [T8], [T5] | Sequential and concurrent payment retries produce one financial row and one payment completion activity. | P2 | S10 |
| FI-06 | Credit notes, refunds, and reversals | Partial | [M11], [B16], [T13] | Unpaid invoice cancellation creates a linked reversing journal entry; credit notes, refunds and payment reversals remain missing. | P1 | S7 |
| FI-07 | Cancel and replace an invoice | Partial | [B8], [M5], [T11], [T13] | Unpaid cancelled invoices return to Draft and reissue with original number/history plus immutable posting/reversal cycles; separate replacement documents and credit notes remain. | P1 | S7 |
| FI-08 | Taxes and fiscal positions | Partial | [M3], [B5] | Manual line percentage only; add tax records, included/excluded policies, exemptions and localization requirements. | P1 | S10 |
| FI-09 | Currencies and exchange rates | Partial | [M7], [B13], [T4], [T6] | Seven two-decimal choices and one locked currency per company; add FX, rate dates and currency precision policies. | P2 | S10 |
| FI-10 | Printable/PDF business documents | Partial | [U3], [U4], [T6] | Browser print is invoked; add persisted/generated PDFs, templates and output verification if required. | P2 | S5 |
| FN-01 | Double-entry ledger and posting periods | Implemented | [M11], [B16], [T13] | Fixed company chart, balanced automatic invoice/payment journals, immutable cancellation reversals, owner posting-date locks and explicit retry-safe historical import. Manual journals and configurable fiscal years remain outside this narrow capability. | P1 | S10 |
| FN-02 | Bank feeds and reconciliation | Missing | [M5], [R2] | Manual payment labels are not reconciliation; add bank lines and matching/reversal rules. | P1 | S11 |
| FN-03 | Financial statements and analytic accounting | Partial | [B16], [U8], [T13] | Date-filtered trial balance with CSV, profit/loss, balance sheet and journal drill-down work; analytic dimensions, opening balances and broader financial statements remain. | P1 | S10 |
| FN-04 | Legal/e-invoice localization | Missing | [M5], [M7] | Choose jurisdiction and validate numbering, legal fields, tax output and electronic submission rules. | P1 | S10 |

## Projects and reporting

| ID | Capability | Status | Repository evidence | Current boundary / next acceptance condition | Priority | Odoo reference |
| --- | --- | --- | --- | --- | --- | --- |
| PJ-01 | Projects, task CRUD, and archive | Implemented | [M8], [B3], [U2], [T4] | The narrow company-scoped project/task record workflow is tested. | P2 | S12 |
| PJ-02 | Task board, assignee, dates, priorities | Partial | [M8], [U2], [T6], [T8] | Fixed stages, assignment and retained inactive-assignee edits work; configurable workflows remain. | P2 | S12 |
| PJ-03 | Timesheets, billing, and profitability | Partial | [M12], [B17], [U9], [T14] | Whole-minute project/task/ticket time, own-member visibility, manager approval, reasoned voids and filtered CSV work; billing, rates and project profitability remain. | P2 | S13 |
| PJ-04 | Dependencies, milestones, and planning | Missing | [M8] | Represent dependencies and scheduling rules; test blocked/rescheduled work. | P2 | S12 |
| RE-01 | Operational dashboard | Partial | [B10], [U5] | Live all-time metrics exist; add date ranges and reconciled definitions. Confirmed sales are not accounting revenue. | P2 | S1 |
| RE-02 | Activity and record audit history | Partial | [M9], [B10], [B12] | Payment retry activity is fixed. Latest twelve summaries still lack field diffs, full navigation, retention/export controls and unique events for other actions. | P1 | S1 |
| RE-03 | Pivots, comparisons, and custom reports | Missing | [U5], [B10] | Add scoped aggregation/filter APIs and exportable reports with acceptance examples. | P2 | S1 |

## Engineering and operations

| ID | Capability | Status | Repository evidence | Current boundary / next acceptance condition | Priority | Odoo reference |
| --- | --- | --- | --- | --- | --- | --- |
| OP-01 | Local Docker setup and migrations | Implemented | [O1], [O2], [T7] | Four-service local stack, migrations and checks pass; verified with fresh isolated Docker volumes. Production hosting is separate. | P1 | S0 |
| OP-02 | Production configuration and server | Missing | [O1], [O2], [O3] | Separate settings, production server/static hosting, HTTPS and secure-cookie policy; resolve deploy-check warnings. | P1 | S0 |
| OP-03 | CI and deployment pipeline | Partial | [O4], [T7] | Container-based GitHub CI is configured and its commands passed locally; hosted execution and deployment promotion remain unverified. | P1 | S0 |
| OP-04 | Backups, restore, and monitoring | Missing | [O1], [R1] | Test backup restoration and add operational alerting; a named volume is not a backup. | P1 | S0 |
| OP-05 | Automated regression coverage | Partial | [T1], [T4], [T5], [T6], [T8], [T9], [T10], [T11], [T12], [T13], [T14] | API/concurrency and real browser suites cover commercial, catalog, accounting and service workflows; current totals are in VERIFICATION.md; broader parity, load and accessibility suites remain. | P1 | S0 |
| OP-06 | Versioned reproducible release | Partial | [O4] | Feature files are modified/untracked beyond starter commit 7040f04; commit reviewed source and validate a clean checkout. | P1 | S0 |
| OP-07 | Numeric record-ID validation | Implemented | [B14], [T8] | Related record IDs require bounded ASCII digits and a positive database range; malformed values return JSON 400. | P2 | S0 |

## Additional applications

| ID | Capability | Status | Repository evidence | Current boundary / next acceptance condition | Priority | Odoo reference |
| --- | --- | --- | --- | --- | --- | --- |
| EX-01 | Employees, attendance, leave, recruitment, payroll | Partial | [M12], [B17], [U9], [T14] | Company work directory, departments, unique employee codes, Team account links and archive/restore work; attendance, leave, recruitment, contracts and payroll remain. | P3 | S13 |
| EX-02 | Manufacturing, BOM, work centers, quality, maintenance | Missing | [R1], [R2], [M6] | Build production/consumption ledgers and operational dependencies, not placeholder tiles. | P3 | S0 |
| EX-03 | Point of sale | Missing | [R1], [R2] | Implement sessions, tills, order/refund flows, hardware/offline boundaries and payment reconciliation. | P3 | S0 |
| EX-04 | Website, eCommerce, and customer portal | Missing | [R1], [R2] | Add public/customer authentication, catalog, checkout and order fulfillment links if in ERP scope. | P3 | S0 |
| EX-05 | Subscriptions and recurring billing | Missing | [M3], [M5], [R2] | Model contracts, renewal schedules, proration, retries and cancellation. | P3 | S0 |
| EX-06 | Marketing automation and events | Missing | [R1], [R2] | Specify contact consent, campaigns, event registration, scheduling and external delivery integrations. | P3 | S0 |
| EX-07 | Helpdesk, knowledge, and appointments | Partial | [M12], [B17], [U9], [T14] | Internal Helpdesk tickets, assignment, statuses, notes/resolution history, task conversion and support-time links work; knowledge base, appointments, SLAs and customer portal remain. | P3 | S14 |
| EX-08 | Documents, Sign, Spreadsheet, and Studio-style customization | Missing | [R1], [R2] | These require separate feature specifications and edition checks; no equivalent subsystem is present. | P3 | S0 |

## Repository evidence map

References below point to the source inspected on the audit date. Line references may move as fixes land.

- [U1]: app registry and launcher, [modules.js](../frontend/src/data/modules.js#L1).
- [U2]: shared catalog forms/boards/pagination, [CatalogView.vue](../frontend/src/views/CatalogView.vue#L24).
- [U3]: order forms/actions, [OrdersView.vue](../frontend/src/views/OrdersView.vue#L47).
- [U4]: invoice forms/actions, [InvoicesView.vue](../frontend/src/views/InvoicesView.vue#L23).
- [U5]: dashboard view, [DashboardView.vue](../frontend/src/views/DashboardView.vue).
- [B1]: active membership and write scope, [access.py](../backend/apps/companies/access.py#L5), [services.py](../backend/apps/business/services.py#L21).
- [B2]: team permission checks, [companies/views.py](../backend/apps/companies/views.py#L101).
- [B3]: catalog field allowlists/relations/validation, [catalog.py](../backend/apps/business/catalog.py#L12).
- [B4]: auth/session APIs, [accounts/views.py](../backend/apps/accounts/views.py#L38).
- [B5]: line calculations and draft save, [services.py](../backend/apps/business/services.py#L101).
- [B6]: stock fulfillment, [services.py](../backend/apps/business/services.py#L179).
- [B7]: order/invoice actions, [views.py](../backend/apps/business/views.py#L125).
- [B8]: invoice generation, [services.py](../backend/apps/business/services.py#L202).
- [B9]: stock API, [views.py](../backend/apps/business/views.py#L222).
- [B10]: dashboard aggregations, [views.py](../backend/apps/business/views.py#L268).
- [B11]: payment validation and idempotency, [services.py](../backend/apps/business/services.py#L219).
- [B12]: payment activity emission, [views.py](../backend/apps/business/views.py#L211).
- [B13]: currency preferences, [views.py](../backend/apps/business/views.py#L251).
- [B14]: ID validation, [services.py](../backend/apps/business/services.py#L43).
- [M1]: Contact, [models.py](../backend/apps/business/models.py#L26).
- [M2]: Product, [models.py](../backend/apps/business/models.py#L60).
- [M3]: Order/OrderLine, [models.py](../backend/apps/business/models.py#L106).
- [M4]: Opportunity, [models.py](../backend/apps/business/models.py#L83).
- [M5]: Invoice/Payment, [models.py](../backend/apps/business/models.py#L152).
- [M6]: StockMovement, [models.py](../backend/apps/business/models.py#L144).
- [M7]: WorkspaceSettings, [models.py](../backend/apps/business/models.py#L19).
- [M8]: Project/Task, [models.py](../backend/apps/business/models.py#L184).
- [M9]: Activity, [models.py](../backend/apps/business/models.py#L204).
- [R1]: frontend route inventory, [router/index.js](../frontend/src/router/index.js#L17).
- [R2]: backend business endpoint inventory, [business/urls.py](../backend/apps/business/urls.py#L5).
- [O1]: local-only service stack, [compose.yml](../compose.yml).
- [O2]: migration/runserver entrypoint, [entrypoint.sh](../backend/entrypoint.sh).
- [O3]: local settings, [settings/local.py](../backend/config/settings/local.py).
- [O4]: working-tree inventory in [the historical audit](REPOSITORY-AUDIT.md#repository-state-and-maintainability) and the new [CI workflow](../.github/workflows/check.yml); hosted execution awaits a reviewed push.
- [T1]: company isolation tests, [business/tests.py](../backend/apps/business/tests.py#L76).
- [T2]: membership role tests, [companies/test_api.py](../backend/apps/companies/test_api.py#L94).
- [T3]: CSRF/session tests, [accounts/test_api.py](../backend/apps/accounts/test_api.py#L52).
- [T4]: commercial workflow tests, [business/tests.py](../backend/apps/business/tests.py).
- [T5]: MySQL concurrency tests, [business/test_concurrency.py](../backend/apps/business/test_concurrency.py).
- [T6]: browser flows, [browser-erp-flow.mjs](../scripts/browser-erp-flow.mjs), [verify-browser.mjs](../scripts/verify-browser.mjs).
- [T7]: repeatable project checks, [check.ps1](../scripts/check.ps1).

The bracketed evidence keys are plain labels. The adjacent links resolve to the inspected source.

- [U6]: document/pagination guards, [forms.js](../frontend/src/composables/forms.js).
- [T8]: audit regression tests, [test_foundation.py](../backend/apps/business/test_foundation.py).
- [T9]: authentication security/concurrency tests, [test_security.py](../backend/apps/accounts/test_security.py), [test_concurrency.py](../backend/apps/accounts/test_concurrency.py).
- [O5]: shared throttling and queued mail, [security.py](../backend/apps/accounts/security.py), [recovery.py](../backend/apps/accounts/recovery.py).
- [U7]: shared UI/catalog components, [component guide](VUE-COMPONENTS.md), [catalog toolbar](../frontend/src/components/catalog/CatalogToolbar.vue), [table](../frontend/src/components/catalog/RecordTable.vue), [CSV UI](../frontend/src/components/catalog/CatalogImport.vue).
- [B15]: filtered catalog and transfer APIs, [catalog.py](../backend/apps/business/catalog.py), [catalog_transfer.py](../backend/apps/business/catalog_transfer.py).
- [M10]: ProductCategory and CatalogImport retry receipt, [models.py](../backend/apps/business/models.py#L42).
- [T10]: catalog API regressions, [test_catalog.py](../backend/apps/business/test_catalog.py), concurrent import retries in [test_concurrency.py](../backend/apps/business/test_concurrency.py), and [browser-catalog-flow.mjs](../scripts/browser-catalog-flow.mjs).
- [T11]: CRM/Sales regressions, [test_crm_sales.py](../backend/apps/business/test_crm_sales.py), concurrency checks in [test_concurrency.py](../backend/apps/business/test_concurrency.py), and [browser-crm-sales-flow.mjs](../scripts/browser-crm-sales-flow.mjs). See [CRM-SALES.md](CRM-SALES.md).
- [T12]: Purchase/Inventory regressions and legacy migration, [test_purchase_inventory.py](../backend/apps/business/test_purchase_inventory.py), concurrency checks in [test_concurrency.py](../backend/apps/business/test_concurrency.py), and [browser-purchase-inventory-flow.mjs](../scripts/browser-purchase-inventory-flow.mjs). See [PURCHASE-INVENTORY.md](PURCHASE-INVENTORY.md).

- [M11]: ledger accounts, entries/lines and date locks, [models.py](../backend/apps/business/models.py).
- [B16]: transactional accounting and scoped reports, [accounting.py](../backend/apps/business/accounting.py), [accounting_views.py](../backend/apps/business/accounting_views.py).
- [U8]: financial reports and journal source navigation, [AccountingView.vue](../frontend/src/views/AccountingView.vue).
- [T13]: accounting acceptance and browser checks, [test_accounting.py](../backend/apps/business/test_accounting.py), [browser-accounting-flow.mjs](../scripts/browser-accounting-flow.mjs), concurrency tests [test_concurrency.py](../backend/apps/business/test_concurrency.py). See [ACCOUNTING-INTEGRATION.md](ACCOUNTING-INTEGRATION.md).

- [M12]: department, employee, ticket, note and timesheet models, [models.py](../backend/apps/business/models.py), additive [migration 0006](../backend/apps/business/migrations/0006_service_operations.py).
- [B17]: scoped service rules/APIs, [operations.py](../backend/apps/business/operations.py), [operations_views.py](../backend/apps/business/operations_views.py), work-directory [catalog.py](../backend/apps/business/catalog.py).
- [U9]: employee directory, [CatalogView.vue](../frontend/src/views/CatalogView.vue), [TimesheetsView.vue](../frontend/src/views/TimesheetsView.vue), [HelpdeskView.vue](../frontend/src/views/HelpdeskView.vue).
- [T14]: service API acceptance tests, [test_operations.py](../backend/apps/business/test_operations.py), concurrent daily-limit/retry/review/task tests [test_concurrency.py](../backend/apps/business/test_concurrency.py), browser owner/member workflows [browser-service-operations-flow.mjs](../scripts/browser-service-operations-flow.mjs).

- [M13]: company warehouse/location models and protected movement endpoints, [models.py](../backend/apps/business/models.py), additive [schema migration](../backend/apps/business/migrations/0007_warehouse_location_schema.py), [in-place backfill](../backend/apps/business/migrations/0008_assign_legacy_stock_locations.py).
- [B18]: locked inventory configuration and endpoint assignment, [locations.py](../backend/apps/business/locations.py), scoped archive-only [APIs](../backend/apps/business/location_views.py).
- [U10]: warehouse/location list, form and hierarchy, [InventoryStructureView.vue](../frontend/src/views/InventoryStructureView.vue), endpoint-aware [StockView.vue](../frontend/src/views/StockView.vue).
- [T15]: INV-01 API and real migration acceptance, [test_warehouse_locations.py](../backend/apps/business/test_warehouse_locations.py), browser owner/member forms in [workspace.spec.ts](../frontend/tests/e2e/workspace.spec.ts). See [INV-01 verification](testing/INV-01-VERIFICATION.md).

## Official Odoo references

Sources were originally consulted on 2026-10-28. CRM quotations, credit notes,
replenishment, and the added service-app references were rechecked on 2026-10-29.
Some direct page opens timed out; indexed official-documentation content was
available. Live edition comparison is not a frozen Odoo-19 entitlement record,
so no row makes an edition entitlement claim.

- S0: [Odoo 19 user documentation](https://www.odoo.com/documentation/19.0/applications.html), [Odoo's official 19.0 repository overview](https://github.com/odoo/odoo/blob/19.0/README.md), and [edition comparison](https://www.odoo.com/page/editions). These establish app families and the need to distinguish editions.
- S1: [Odoo 19 essentials](https://www.odoo.com/documentation/19.0/applications/essentials/) and [reporting](https://www.odoo.com/documentation/19.0/applications/essentials/reporting.html). This baseline includes configurable searches/activities and reporting beyond fixed dashboards.
- S2: [Odoo 19 access rights](https://www.odoo.com/documentation/19.0/applications/general/users/access_rights.html) and [users](https://www.odoo.com/documentation/19.0/applications/general/users.html). Per-app groups and document-level access are deeper than KERP's company-wide write role.
- S3: [Odoo 19 import/export](https://www.odoo.com/documentation/19.0/applications/essentials/export_import_data.html). KERP now has bounded catalog CSV creation/export; XLSX, update imports and broader document mapping remain.
- S4: [Odoo 19 supply chain](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp.html). Product, procurement, location and valuation scope exceeds KERP's single-pool ledger.
- S5: [Odoo 19 Sales](https://www.odoo.com/documentation/19.0/applications/sales/sales.html), [quotation creation](https://www.odoo.com/documentation/19.0/applications/sales/sales/sales_quotations/create_quotations.html), and [invoicing methods](https://www.odoo.com/documentation/19.0/applications/sales/sales/invoicing.html).
- S6: [Odoo 19 quotation creation from CRM](https://www.odoo.com/documentation/19.0/applications/sales/crm/acquire_leads/send_quotes.html) and [lead conversion](https://www.odoo.com/documentation/19.0/applications/sales/crm/acquire_leads/convert.html). KERP links opportunities to quotations; a separate lead-conversion workflow remains outside its scope.
- S7: [Odoo 19 credit notes/refunds](https://www.odoo.com/documentation/19.0/applications/finance/accounting/customer_invoices/credit_notes.html). KERP has unpaid cancellation journal reversals; credit notes and refunds remain separate; this is feature comparison, not jurisdiction-specific legal advice.
- S8: [Odoo 19 product tracking](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/management/lots_serial_numbers.html) and [serial numbers](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/product_management/product_tracking/create_sn.html).
- S9: [Odoo 19 replenishment](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/warehouses_storage/replenishment.html). KERP's threshold count does not generate replenishment suggestions/orders.
- S10: [Odoo 19 Finance](https://www.odoo.com/documentation/19.0/applications/finance.html) and [Accounting/Invoicing](https://www.odoo.com/documentation/19.0/applications/finance/accounting.html). KERP now has a fixed document-derived ledger and basic statements; manual journals, bank matching and localization remain separate.
- S11: [Odoo 19 bank reconciliation](https://www.odoo.com/documentation/19.0/applications/finance/accounting/bank/reconciliation.html).
- S12: [Odoo 19 task management](https://www.odoo.com/documentation/19.0/applications/services/project/tasks.html). Project depth includes capabilities such as dependencies beyond a fixed task board.
- S13: [Odoo 19 departments](https://www.odoo.com/documentation/19.0/applications/hr/employees/departments.html) and [Timesheets](https://www.odoo.com/documentation/19.0/applications/services/timesheets.html). KERP has flat departments and manual reviewed time; department hierarchy, timers and time billing remain outside its implementation.
- S14: [Odoo 19 ticket channels](https://www.odoo.com/documentation/19.0/applications/services/helpdesk/overview/receiving_tickets.html) and [service-level agreements](https://www.odoo.com/documentation/19.0/applications/services/helpdesk/overview/sla.html). KERP's internal tickets do not supply those external channels or SLA policies.

## Practical delivery order

1. Keep the completed foundation regressions green; finish ingress/permission and production release work before deployment.
2. Extend the linked CRM/Sales flow with quantity-based partial fulfillment/invoicing.
3. Add returns/credit notes, stock/payment reversals, and per-app permissions.
4. Extend the accounting foundation with opening balances, bank matching and chosen jurisdiction requirements.
5. Extend catalog CSV transfers to XLSX/document workflows, deeper reporting, and operations/release controls.
6. Select additional app families from EX-01 to EX-08 with explicit acceptance scope.

A full parity commitment still needs an agreed Odoo edition/version, installed apps, jurisdiction, integrations, performance target, and acceptance suite. This audit supplies a concrete starting checklist rather than an unsupported "100%" claim.

