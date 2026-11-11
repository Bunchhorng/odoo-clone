# Odoo-style ERP: feature coverage

The repository now has a [reproduced audit](REPOSITORY-AUDIT.md) and an
[evidence-based Odoo parity matrix](ODOO-PARITY-MATRIX.md), with a
[spreadsheet copy](ODOO-PARITY-MATRIX.csv). Use those for current defect status,
capability acceptance conditions, and implementation priorities. The broad overview
below does not imply that its working features are defect-free.

The [E2E/parity verification pass](E2E-PARITY.md) records the latest test evidence,
implemented-capability traceability, and repeatable Markdown/CSV consistency checks.

The requested direction is an ERP application with an Odoo-style interface and
integrated business modules. KERP retains its Django + Vue + MySQL architecture.
It is not Odoo itself, and the current implementation does **not** have 100% of
Odoo's applications or feature depth. No percentage is claimed without a defined
edition, version, installed app set, and acceptance checklist.

The implementation uses an app launcher, module navigation, searchable cards/lists,
record dialogs, Kanban boards, document forms, status actions, company selection,
and connected business workflows. Each visible app tile opens implemented screens;
unimplemented applications are not presented as working apps.

## Current coverage

| Area | Working in KERP | Remaining before broad Odoo parity |
| --- | --- | --- |
| Application shell | Purple navigation, app grid/search, module menu, responsive screens | Saved searches, user favorites, command palette, configurable views, translations |
| Companies and users | Login/logout, session/CSRF, shared throttles, password change/recovery, companies/team roles | Invitations, MFA/SSO, per-app permissions, deeper user preferences |
| Contacts | Customer/supplier/both, organization, contact details, phone search, role filter, sorting, cards/list, bulk archive/restore, validated CSV import/export | Parent-child address trees, duplicate merging, attachments, full cross-app history, XLSX |
| CRM | Five-stage pipeline, drag/drop and keyboard stage changes, revenue, probability, dates, notes, linked quotations and navigation | Custom stages, activities/calendar, email, automated lead scoring |
| Product catalog | SKU, goods/services, categories, barcode storage, prices/cost, units, reorder threshold, filters/sorting, bulk archive/restore, validated CSV import/export | Variants, images, barcode scanning, multiple units and price lists, XLSX |
| Sales | CRM-linked draft quotations, editable lines, tax percentage, decimal totals, version-checked saves/transitions, full delivery, invoice creation, print | Discounts, signatures, email, customer portal, partial delivery/invoicing, subscriptions, returns |
| Purchase | RFQs, supplier lines/costs, confirmation, partial/full receipts, line quantity tracking, supplier returns for replacement, vendor bill creation | Vendor price rules, tendering, approvals, replenishment, receipt/bill matching, partial billing and credits |
| Inventory | Searchable/filterable movement ledger, on-hand balances, retry-safe adjustments, linked reversals, no-negative-stock rule, idempotent receipts/deliveries, company warehouses and validated location hierarchies, in-place legacy endpoint assignment (INV-01) | Per-operation warehouse routing, transfers, reservations, lots/serials, picking routes, valuation, scanning |
| Invoicing | Order-based customer invoices/vendor bills, snapshots, issue/cancel, unpaid cancellation correction, due dates, manual partial/full payments, print/PDF via browser | Credit notes, standalone invoices, legal localization, electronic invoices, automated payment processing |
| Accounting | Fixed chart, balanced invoice/payment journals, unpaid cancellation reversals, owner date locks, explicit historical import, trial balance/CSV, profit/loss and balance sheet, linked source documents | Manual/opening entries, configurable chart, credit notes, tax reports/localization, bank feeds/reconciliation, assets and analytic accounting |
| Projects | Projects, customer link, tasks, assignee, due dates, priorities, Kanban/list, archive/restore, linked project/task/support time | Dependencies, milestones, planning, recurring tasks, time billing and profitability |
| Timesheets | Whole-minute draft/submitted/approved time, manager review, reasoned voids, own-member visibility, filtered summaries/CSV, project/task/ticket links | Timers, billable rates, invoicing, profitability, planning and configurable approval policies |
| Reporting | Live company dashboard, pipeline bars, activity, recent orders, operational counts; date-filtered financial reports/CSV and journal drill-down; catalog CSV transfers | Operational date filters, pivots, custom reports, comparisons, forecast modeling |
| HR | Company-visible employee work directory, departments, employee codes, Team account links, archive/restore | Private HR roles/data, attendance, leave, recruitment, contracts, appraisals, payroll/localization |
| Manufacturing | Not implemented | Bills of materials, manufacturing/work orders, work centers, MRP, quality, maintenance |
| POS | Not implemented | Sessions, tills, receipts, offline use, hardware, returns, payments |
| Website/eCommerce | Not implemented | Website builder, public store, checkout, customer portal, SEO |
| Helpdesk | Internal ticket CRUD, assignment, statuses, overdue/mine filters, notes and full resolution history, task conversion, support-time links | Customer portal, email, SLAs, knowledge base and appointments |
| Marketing | Not implemented | Email/SMS/social campaigns, consent, automations and events |
| Production operations | Local Docker, migrations, tests, health checks, database-backed authentication throttles, CI configuration | Deployment settings, HTTPS, trusted-ingress throttle tuning, backups/restore, monitoring, release pipeline |

The [INV-01 delivery](INVENTORY-V2-INV-01.md) keeps all existing posting APIs on the default warehouse. Additional warehouse/location configuration does not claim implemented transfers or reservations.

## Design references

The target app relationships and workflows were checked against Odoo's official
materials, accessed 2026-10-28:

- [Odoo CRM features](https://www.odoo.com/app/crm-features): pipeline management,
  customer records, and related sales workflows.
- [Odoo sales quotations](https://www.odoo.com/documentation/master/applications/sales/sales/sales_quotations.html):
  quotation, confirmation, delivery, invoice, and payment lifecycle.
- [Odoo accounting and invoicing](https://www.odoo.com/documentation/19.0/applications/finance/accounting.html):
  the distinction between invoice management and a full accounting system.

These references describe Odoo, not a promise that every listed behavior is
implemented in KERP. The working/remaining columns above describe this repository.

## How to finish each remaining area

1. Select the exact workflow, edition/version behavior, fields, and permission rules.
2. Add API/model acceptance tests, including company isolation and concurrent writes.
3. Implement complete database-to-screen workflows, including failure and empty states.
4. Verify real browser behavior on desktop/mobile.
5. Update this matrix and the user/API guides with what passed and what remains.

Recommended next depth improvements are partial deliveries/invoices,
returns/credit notes, per-module permissions, and bank reconciliation/opening
balances on top of the [accounting foundation](ACCOUNTING-INTEGRATION.md). Country-specific tax/accounting behavior needs its own explicit
requirements and validation before use for real statutory records.

The [service application guide](SERVICE-APPLICATIONS.md) records the Employees,
Timesheets and Helpdesk scope, own-time access rules and remaining app families.
