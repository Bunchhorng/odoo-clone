# Odoo-style ERP: feature coverage

The repository now has a [reproduced audit](REPOSITORY-AUDIT.md) and an
[evidence-based Odoo parity matrix](ODOO-PARITY-MATRIX.md), with a
[spreadsheet copy](ODOO-PARITY-MATRIX.csv). Use those for current defect status,
capability acceptance conditions, and implementation priorities. The broad overview
below does not imply that its working features are defect-free.

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
| CRM | Five-stage pipeline, drag/drop and keyboard stage changes, revenue, probability, dates, notes | Custom stages, activities/calendar, opportunity-to-quotation link, email, automated lead scoring |
| Product catalog | SKU, goods/services, categories, barcode storage, prices/cost, units, reorder threshold, filters/sorting, bulk archive/restore, validated CSV import/export | Variants, images, barcode scanning, multiple units and price lists, XLSX |
| Sales | Draft quotations, editable lines, tax percentage, decimal totals, confirmation, full delivery, invoice creation, print | Discounts, signatures, email, customer portal, partial delivery/invoicing, subscriptions, returns |
| Purchase | RFQs, supplier lines/costs, confirmation, full receipts, vendor bill creation | Vendor price rules, tendering, approvals, replenishment, partial receipts, returns |
| Inventory | Movement ledger, on-hand balances, signed adjustments, no-negative-stock rule, idempotent receipts/deliveries | Warehouses/locations, transfers, reservations, lots/serials, picking routes, valuation, scanning |
| Invoicing | Order-based customer invoices/vendor bills, snapshots, issue/cancel, due dates, manual partial/full payments, print/PDF via browser | Credit notes, standalone invoices, legal localization, electronic invoices, automated payment processing |
| Accounting | Receivable/payable balances from manual invoices and payments | Double-entry journals, chart of accounts, tax reports, fiscal periods, bank feeds/reconciliation, assets, accounting statements |
| Projects | Projects, customer link, tasks, assignee, due dates, priorities, Kanban/list, archive/restore | Timesheets, dependencies, milestones, planning, recurring tasks, profitability |
| Reporting | Live company dashboard, pipeline bars, activity, recent orders, operational counts; catalog CSV transfers | Date filters, pivots, custom reports, report exports, comparisons, forecast modeling |
| HR | Not implemented | Employees, departments, attendance, leave, recruitment, appraisals, payroll/localization |
| Manufacturing | Not implemented | Bills of materials, manufacturing/work orders, work centers, MRP, quality, maintenance |
| POS | Not implemented | Sessions, tills, receipts, offline use, hardware, returns, payments |
| Website/eCommerce | Not implemented | Website builder, public store, checkout, customer portal, SEO |
| Marketing/helpdesk | Not implemented | Email/SMS/social campaigns, automations, helpdesk, knowledge, appointments, events |
| Production operations | Local Docker, migrations, tests, health checks | Deployment settings, HTTPS, rate limits, backups/restore, monitoring, release pipeline |

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

Recommended next depth improvements are quotation conversion from CRM, partial
deliveries/invoices, returns/credit notes, per-module permissions, and accounting
foundations. Country-specific tax/accounting behavior needs its own explicit
requirements and validation before use for real statutory records.
