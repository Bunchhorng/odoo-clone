# KERP — Prompt 09: Complete ERP Database Seeders and Demo Data

## Role

Act as a Senior Django Backend Developer, MySQL Database Architect, ERP Functional Consultant, Odoo 19 Business Analyst, and QA Automation Engineer.

Project: KERP

Technology:
- Django
- Vue.js
- MySQL
- Docker Compose

Reference: Odoo 19 Community and Enterprise business concepts.

## Main Objective

Create a complete, realistic, interconnected, and repeatable database seeding system for the existing KERP application.

The seeders must populate all implemented ERP applications with meaningful demonstration data, including related commercial, inventory, accounting, employee, project, and support workflows.

The objective is to make KERP immediately useful for demonstrations, UI testing, reporting verification, and end-to-end development testing.

Do not create random, unrelated CRUD records.

Do not implement a new business module solely to satisfy demo-data targets.

---

# Phase 1 — Inspect Existing Database Architecture

Before implementing seeders:

1. Inspect all Django models.
2. Inspect database migrations.
3. Inspect company and user relationships.
4. Inspect role and permission models.
5. Inspect existing seeders, fixtures, and management commands.
6. Inspect business service functions.
7. Inspect document numbering systems.
8. Inspect inventory movement logic.
9. Inspect accounting posting logic.
10. Inspect ODOO-PARITY-MATRIX.md and VERIFICATION.md.

Identify model dependencies and required creation order.

Reuse existing fixtures and management commands where appropriate.

Do not assume models exist based only on the roadmap.

Produce a data-seeding dependency map.

---

# Phase 2 — Create Django Management Commands

Implement a reusable seeding system using Django management commands.

Proposed structure:

```text
backend/
└── apps/
    └── core/
        └── management/
            └── commands/
                ├── seed_demo.py
                ├── seed_companies.py
                ├── seed_users.py
                ├── seed_contacts.py
                ├── seed_products.py
                ├── seed_sales.py
                ├── seed_purchase.py
                ├── seed_inventory.py
                ├── seed_accounting.py
                ├── seed_hr.py
                ├── seed_projects.py
                └── seed_helpdesk.py
```

Adapt this structure to the current project.

Create a main command:

`python manage.py seed_demo`

Support options:

- `--profile small`
- `--profile medium`
- `--profile large`
- `--seed 42`
- `--company DEMO`
- `--dry-run`
- `--verify`
- `--reset-demo`

Only implement options that work and have automated tests.

## Seeder Requirements

- Deterministic data using a configurable random seed.
- Idempotent execution.
- Safe database transactions.
- Explicit demo-data identification.
- No accidental modification of real business records.
- Unique document numbers.
- Valid foreign keys.
- Valid company relationships.
- Safe retry behavior.
- Business workflow consistency.
- Readable progress and error reporting.

Use stable external keys or demo namespace identifiers to identify previously seeded records.

Do not rely on guessed primary-key IDs.

---

# Phase 3 — Development Environment Protection

Seeders must be safe.

Requirements:

1. Default to development/test environments only.
2. Refuse execution in production.
3. Never delete real customer, accounting, or inventory records.
4. Require an explicit confirmation flag for demo-data reset.
5. Restrict reset to records identified as demo data.
6. Refuse reset if demo records have dependencies on real records.
7. Do not overwrite existing production configuration.
8. Never use real personal information or secrets.
9. Never include real payment credentials.

Use isolated development and test databases when possible.

The reset operation must be tested separately and must not use unrestricted database truncation.

---

# Phase 4 — Company Seeder

Create three fictional companies:

1. KERP Demo Trading Co., Ltd.
2. KERP Demo Retail Co., Ltd.
3. KERP Demo Services Co., Ltd.

Use explicitly fictional addresses, contact details, and registration information.

Create company-specific:

- Default currency.
- Company preferences.
- Document sequences.
- Warehouses, where applicable.
- Accounting journals.
- Chart of accounts.
- Authorized users.
- Role assignments.

Use the existing company currency model and supported currencies.

Never mix company records unintentionally.

---

# Phase 5 — Users and Roles Seeder

Create 20 fictional demonstration users.

Example roles:

- Company Owner.
- Administrator.
- Sales Manager.
- Sales Representative.
- Purchase Manager.
- Inventory Manager.
- Warehouse Operator.
- Accountant.
- Accounting Manager.
- HR Manager.
- Employee.
- Project Manager.
- Helpdesk Agent.

Use the actual implemented permission system.

Assign users to companies according to their roles.

Create at least one cross-company authorized administrator and users restricted to a single company.

Security requirements:

- No shared hardcoded credentials in source code.
- Passwords supplied through environment variables or generated securely.
- Never print passwords in logs.
- Do not create privileged demo users in production.
- Preserve the last-owner rule.

Test permitted and denied access across companies.

---

# Phase 6 — Contacts Seeder

Create:

- 100 fictional customers.
- 30 fictional suppliers.
- Billing and shipping addresses where supported.
- Company/contact hierarchy where implemented.
- Customer and supplier classifications.
- Contact phone numbers and emails using reserved example domains.

Suggested customer groups:

- Retail Customers.
- Wholesale Customers.
- Corporate Customers.
- VIP Customers.

Create contacts with realistic but fictional business information.

Ensure names, emails, and tax identifiers do not impersonate real individuals or companies.

---

# Phase 7 — Product Seeder

Create 150 products across 15 categories.

Suggested categories:

1. Laptops.
2. Smartphones.
3. Tablets.
4. Computer Accessories.
5. Networking Equipment.
6. Office Equipment.
7. Printers.
8. Storage Devices.
9. Monitors.
10. Electronics.
11. Furniture.
12. Office Supplies.
13. Software Services.
14. IT Support Services.
15. Consulting Services.

Include:

- SKU.
- Product name.
- Category.
- Product type.
- Unit of measure.
- Sales price.
- Purchase cost.
- Barcode where supported.
- Tax configuration.
- Product variants where implemented.
- Supplier association where supported.

Use realistic price and cost relationships.

Avoid unsupported product states or invalid variants.

---

# Phase 8 — Warehouse and Inventory Seeder

Create:

- 4 warehouses distributed across authorized companies.
- Approximately 20 stock locations.
- Product stock balances.
- Receiving history.
- Internal transfers.
- Sales deliveries.
- Inventory adjustments.
- Supplier returns.
- Customer returns where supported.
- Reservations and backorders where implemented.

Example warehouse organization:

```text
Main Warehouse
├── Stock
│   ├── Shelf A
│   └── Shelf B
├── Input
├── Output
└── Quality
```

Use inventory services to perform real stock operations.

Do not update stock quantity fields directly if the domain uses a movement ledger.

## Required scenarios

1. Product with available stock.
2. Product with low stock.
3. Product out of stock.
4. Fully reserved product.
5. Partially delivered Sales Order.
6. Pending backorder.
7. Completed internal transfer.
8. Supplier receipt.
9. Customer return.

Only generate scenarios supported by implemented workflows.

Verify physical quantity conservation and stock history.

---

# Phase 9 — CRM Seeder

Create approximately 60 opportunities.

Include:

- Leads.
- Qualified opportunities.
- Different pipeline stages.
- Expected revenue.
- Probability.
- Customer association.
- Salesperson.
- Follow-up activities.
- Won opportunities.
- Lost opportunities.

Link selected won opportunities to actual Sales quotations.

Preserve valid CRM stage transitions.

---

# Phase 10 — Sales Seeder

Create approximately 120 sales quotations/orders.

Include:

- Draft quotations.
- Sent quotations.
- Confirmed orders.
- Partially delivered orders.
- Fully delivered orders.
- Partially invoiced orders.
- Fully invoiced orders.
- Cancelled orders where supported.

Include multiple products per order.

Use applicable pricelists, taxes, discounts, and currency rules only when those features exist.

## Required business scenarios

Scenario A:
Quotation → Confirmation → Full Delivery → Invoice → Full Payment.

Scenario B:
Quotation → Confirmation → Partial Delivery → Backorder → Multiple Invoices.

Scenario C:
Delivered Order → Customer Return → Credit Note → Refund.

Scenario D:
Confirmed Order → Invoice → Partial Payment.

Use existing Django business services rather than directly forcing order states.

If a scenario is unsupported, record it as skipped with the missing dependency.

---

# Phase 11 — Purchase Seeder

Create approximately 50 purchase orders.

Include:

- Draft RFQs.
- Confirmed Purchase Orders.
- Partial receipts.
- Full receipts.
- Supplier returns.
- Vendor bills.
- Partially paid bills.
- Fully paid bills.

Generate valid receipt and billing quantities.

Do not create supplier bills disconnected from the corresponding Purchase workflow unless standalone vendor bills are supported.

---

# Phase 12 — Accounting Seeder

Create realistic accounting records using the existing posting services.

Include:

- Chart of accounts.
- Journals.
- Customer invoices.
- Vendor bills.
- Payments.
- Partial payments.
- General journal entries.
- Credit notes where supported.
- Bank statements where supported.
- Reconciliations where supported.
- Opening balances where supported.

## Critical requirements

- Every posted journal must balance.
- Every customer invoice must have a valid company and partner.
- Payment allocations cannot exceed eligible balances without an explicit overpayment policy.
- Credit notes must reference appropriate source transactions.
- No duplicate postings.
- No cross-company journal references.
- Financial reports must reconcile.

Do not directly insert fake balanced numbers into reporting tables.

Use real posted transactions to generate financial reports.

---

# Phase 13 — Employee and HR Seeder

Create approximately 30 fictional employees.

Include:

- Departments.
- Job positions.
- Managers.
- Employee codes.
- Team account links.
- Employment status.

Where implemented, also create:

- Attendance records.
- Working schedules.
- Leave requests.
- Approved leave.
- Recruitment applications.
- Employment contracts.
- Payroll periods.
- Demo payslips.

Use fictional private employee information.

Do not represent demonstration payroll calculations as statutory compliance.

---

# Phase 14 — Project and Timesheet Seeder

Create:

- 15 projects.
- 100 tasks.
- 200 timesheet records.

Include:

- Project managers.
- Assigned members.
- Task stages.
- Priorities.
- Deadlines.
- Customer links.
- Draft timesheets.
- Submitted timesheets.
- Approved timesheets.
- Voided timesheets with valid reasons.

Where supported, create billable service time and invoice allocations.

Do not bypass existing approval rules.

---

# Phase 15 — Helpdesk Seeder

Create approximately 80 support tickets.

Include:

- New tickets.
- Assigned tickets.
- In-progress tickets.
- Resolved tickets.
- Closed tickets.
- Different priorities.
- Support agents.
- Linked customers.
- Linked tasks.
- Timesheet records.
- Internal notes.
- SLA scenarios where supported.

Create coherent ticket histories using existing services.

---

# Phase 16 — Additional ERP Applications

Seed the following only if implemented and verified:

## Manufacturing
- Bills of Materials.
- Manufacturing orders.
- Component consumption.
- Completed production.
- Scrap records.

## POS
- POS sessions.
- Cashiers.
- Orders.
- Payments.
- Refunds.
- Session closing records.

## eCommerce
- Storefront products.
- Customer accounts.
- Shopping carts.
- Checkout orders.
- Payments.
- Fulfillment records.

## Subscriptions
- Subscription plans.
- Active subscriptions.
- Recurring invoices.
- Cancelled subscriptions.

## Marketing
- Campaigns.
- Fictional opted-in contacts.
- Campaign events.

## Documents
- Sample documents.
- Folder permissions.
- Attachment relationships.

Never seed unimplemented workflows by manually fabricating terminal states.

---

# Phase 17 — Historical and Dashboard Data

Create records distributed over a configurable historical period, such as the previous 12 months.

Include realistic variation in:

- Sales volume.
- Purchase volume.
- Inventory movement.
- Customer payments.
- Project activity.
- Helpdesk demand.

Do not alter accounting or inventory posting dates in ways that violate fiscal locks or historical consistency.

Use legitimate business services and time-aware fixtures.

The resulting dashboard should show meaningful trends, not artificial identical totals.

---

# Phase 18 — Verification Tests

Implement automated tests for:

1. First seeding execution.
2. Running seeders twice.
3. Deterministic results with the same seed.
4. Unique document references.
5. Valid model relationships.
6. Cross-company isolation.
7. Balanced accounting entries.
8. Correct stock balances.
9. Valid sales quantities.
10. Correct invoice/payment balances.
11. Valid employee and department relationships.
12. Valid timesheet approvals.
13. Valid Helpdesk history.
14. Safe demo reset.
15. Production seeding refusal.
16. Missing-module handling.
17. Transaction rollback after failure.
18. Reproducible dashboard totals.

Run existing backend and browser regression tests.

Provide exact commands and results.

---

# Phase 19 — Seeder Verification Report

After implementation, produce:

## KERP Demo Seeder Report

- Current Git commit.
- Seeder command names.
- Files changed.
- Models populated.
- Count of records per module.
- Company-specific counts.
- Supported business workflows.
- Skipped scenarios and reasons.
- Validation results.
- Reconciliation checks.
- Test commands and outcomes.
- Known limitations.

Update the README with:

- How to seed the database.
- How to select profiles.
- How to verify seed data.
- How to reset demo records safely.
- Docker commands.
- Credential configuration.

Do not report success unless actual database verification passes.

---

# First Implementation Assignment

Start with:

**SEED-01 — Core Demo Data Foundation**

1. Audit existing models and dependencies.
2. Identify existing fixture/management command patterns.
3. Design deterministic demo identifiers.
4. Implement environment safety checks.
5. Create the main `seed_demo` command.
6. Seed companies, users, roles, contacts, and products.
7. Add idempotency tests.
8. Add multi-company isolation tests.
9. Verify seeded records and counts.
10. Update documentation.

After SEED-01 passes, continue with the next dependency-ready seeding milestones:

- SEED-02: Inventory.
- SEED-03: CRM and Sales.
- SEED-04: Purchase.
- SEED-05: Accounting and Payments.
- SEED-06: HR, Projects, Timesheets, and Helpdesk.
- SEED-07: Additional implemented applications.
- SEED-08: Historical data, reporting, and full verification.

Work incrementally and never bypass core business rules simply to populate demo data.

**Final Objective:** Deliver a complete, safe, repeatable, Odoo-style KERP demo database that demonstrates real integrated ERP workflows.