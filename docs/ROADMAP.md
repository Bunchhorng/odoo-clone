# Step-by-step roadmap toward an Odoo-style ERP

The project direction now includes an Odoo-style ERP application and business
modules. The [coverage matrix](ODOO-COVERAGE.md) distinguishes implemented core
workflows from advanced features and applications still to build.

## Steps delivered

1. **Development foundation:** Docker, Django/Vue/MySQL, health checks, migrations,
   isolated tests, setup documentation, Windows startup/check scripts.
2. **Login and company access:** session/CSRF, company creation/switching, team
   roles, last-owner protection, active access checks.
3. **Application shell:** app grid/search, app menu, purple navigation, module tabs,
   record forms, cards/lists, Kanban, responsive layouts.
4. **Contacts and catalog:** customer/supplier contacts, SKU products, goods/services,
   prices/costs, search, archiving, company-scoped relations.
5. **CRM and projects:** fixed-stage opportunity pipeline, probabilities/revenue,
   projects, assigned tasks, priorities/dates, drag/drop and keyboard stage changes.
6. **Sales and purchase:** draft quotations/RFQs, decimal line totals and tax
   percentages, document numbering, confirmed immutable orders, cancellation rules.
7. **Inventory:** stock movement ledger, opening/manual adjustments, full receipts
   and deliveries, negative-stock prevention, repeated fulfillment protection.
8. **Invoices and manual payments:** customer invoices/vendor bills from orders,
   snapshots, issue/cancel, due dates, partial/full payments, retry protection, print.
9. **Business dashboard and demo:** live totals, pipeline, low stock, tasks, recent
   orders/activity, isolated repeatable sample company, workflow and API guides.
10. **CRM and Sales connection:** prefilled linked quotations and navigation,
    document-version conflict protection, retained archived draft selections,
    retry-safe completion activity, and unpaid cancelled-invoice correction.
11. **Purchase and Inventory:** partial goods receipts with numbered history,
    received/remaining quantities, supplier returns awaiting replacement, filtered
    stock tracing, adjustment retry IDs and reversals preserving original entries.
12. **Cross-module accounting:** order/invoice/stock/journal source links, balanced
    invoice/payment postings, unpaid cancellation reversals, owner date locks,
    explicit historical import and date-filtered financial reports/CSV.

13. **Employees, Timesheets and Helpdesk:** department/work directories linked to
    Team, own/team time with submission/review/voiding and CSV, internal support
    tickets with notes/resolution history, task conversion and support-time links.

Delivered means the core behavior above is implemented; it does not mean complete
Odoo app parity. The ledger has a fixed chart and document-derived postings;
manual journals, opening balances, valuation and localization remain separate.

## Next development passes

### 1. Deepen the current commercial workflow

- Add sales/purchase-specific access roles and approval thresholds.
- Add partial sales deliveries/backorders, permanent-return credits, multi-location
  transfers/reservations, and receipt/bill matching policies.
- Add partial invoices, standalone invoices, credit notes, payment reversals.
- Add product variants, images, barcode scanning, unit conversions, discounts, and pricelists.
- Add record history, attachments, XLSX/document import/export, and date-filtered reports.

### 2. Deepen accounting and choose localization

The [accounting foundation](ACCOUNTING-INTEGRATION.md) supplies a fixed chart,
balanced document journals, posting locks, reversals and basic reports. Next add
opening balances, manual entries, custom accounts, bank reconciliation, credit
notes, analytic dimensions and inventory valuation. Specify the business's country
and accounting/tax requirements before legal invoice formats or localized tax reports are implemented.
Use accounting acceptance examples and reconciliation tests, not visual similarity,
to establish correctness.

### 3. Add service and organization apps

The [service apps](SERVICE-APPLICATIONS.md) now supply employee/department
directories, reviewed project time and internal Helpdesk. Next add leave/attendance,
recruitment, planning, expenses, knowledge, documents, appointments and calendar.
Define payroll/localization separately. Extend project work with dependencies,
milestones, time billing and profitability.

### 4. Add operations and customer-facing apps

Manufacturing/BOMs/MRP, quality/maintenance, POS, subscriptions, website/eCommerce,
customer portal, email/SMS marketing, events, and external integrations. Each needs
its own complete requirements, data model, API, UI, and tests.

### 5. Prepare a production release

Production application/static hosting, HTTPS/secure cookies, secret management,
trusted-ingress throttle tuning, external recovery-mail validation/MFA, audit retention, backups/restore drills,
monitoring, release automation, data migration, and load testing.

## Definition of done for each pass

1. Define fields, permissions, transitions, and acceptance examples.
2. Implement company-scoped models, migrations, and transactional APIs.
3. Complete the user workflow with loading, empty, error, and success states.
4. Test role restrictions, invalid inputs, cross-company links, and concurrency.
5. Run Django checks/migration checks/tests, Vue build, and actual browser checks.
6. Update [ERP-GUIDE.md](ERP-GUIDE.md), [ERP-API.md](ERP-API.md), and coverage.

## Foundation follow-up delivered

[Docker + ERP Core + Authentication](FOUNDATION.md) closes A-01 through A-05,
adds password change/recovery and database-backed throttles, adds CI configuration,
and verifies a fresh-volume stack. That milestone passed 78 backend tests;
the browser suite had 16 passing workflow groups at that milestone. Remaining business and production
work above is still tracked in the parity matrix.

## Vue components and Contacts/Products delivered

The [catalog phase](CONTACTS-PRODUCTS.md) adds reusable Vue buttons, fields, notices,
badges, dialogs, empty states, pagination, toolbars and tables. Contacts and Products
add company-scoped filtering/sorting, confirmed bulk archive/restore, previewed
atomic CSV imports and filtered exports. Products add categories and barcode
storage. The [component guide](VUE-COMPONENTS.md) explains how to extend the system;
[VERIFICATION.md](VERIFICATION.md) records current test totals. Remaining work
includes saved searches/grouping, contact hierarchy/merge, XLSX, product variants,
images, scanning and more advanced pricing.
