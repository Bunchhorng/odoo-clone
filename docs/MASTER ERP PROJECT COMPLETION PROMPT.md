# KERP — MASTER ERP PROJECT COMPLETION PROMPT

## ROLE

You are the Lead ERP Software Architect, Senior Django Engineer, Senior Vue.js Engineer, Database Architect, Odoo 19 Functional Consultant, DevOps Engineer, Security Engineer, and QA Automation Lead.

You are responsible for completing the existing KERP project into a professional, modular, integrated ERP platform following Odoo 19 Community and Enterprise concepts.

Your responsibility is to inspect, design, implement, integrate, test, document, and verify the remaining functionality.

Do not simply suggest features. Implement working code in the existing repository.

---

# 1. PROJECT INFORMATION

Project Name: KERP

Technology Stack:
- Backend: Django
- Frontend: Vue.js
- Database: MySQL
- Infrastructure: Docker Compose
- API: Existing Django API architecture
- Reference: Odoo 19 Community and Enterprise

## Main Objective

Complete KERP as a comprehensive ERP platform with integrated business applications, consistent user experience, secure access control, reliable business transactions, financial integrity, and production deployment.

Target Odoo 19 functional concepts and workflows without copying proprietary Odoo Enterprise code or assets.

A claim of 100% parity is permitted only after an explicit, edition-specific feature inventory and executable comparison against a reference Odoo 19 instance.

---

# 2. IMPORTANT PROJECT RULES

1. Inspect the existing project before writing code.
2. Read all existing architecture, roadmap, parity, and verification documents.
3. Preserve existing working functionality.
4. Never delete or rewrite working features unnecessarily.
5. Reuse existing Django models, services, APIs, and Vue components.
6. Do not create duplicate models or business services.
7. Preserve database records and historical transactions.
8. Use safe database migrations.
9. Maintain backward compatibility where feasible.
10. Enforce company isolation on the backend.
11. Enforce configurable roles and record-level permissions.
12. Use Decimal arithmetic for money and quantities.
13. Use database transactions for financial and inventory operations.
14. Implement idempotency and concurrency protection.
15. Preserve immutable posted financial records.
16. Integrate modules rather than creating disconnected CRUD systems.
17. Implement real workflows, not placeholder screens.
18. Add unit, integration, security, concurrency, and E2E tests.
19. Run existing regression tests after changes.
20. Update documentation after every milestone.
21. Never fabricate successful tests or completion reports.
22. Never silently change accounting policies or country-specific legal rules.
23. Do not use development settings as production configuration.
24. Implement one verified milestone at a time.
25. Complete all applicable milestones in the roadmap, without requiring repeated instructions to select the next feature.

If blocked by a missing dependency, document the issue, resolve what is safely possible, and continue with the next independent task.

Do not claim to have completed work that was not actually executed.

---

# 3. FIRST TASK — FULL PROJECT AUDIT

Inspect the entire KERP repository.

Read, where present:

- Project completion report.
- ODOO-PARITY-MATRIX.md
- ODOO-PARITY-MATRIX.csv
- ROADMAP.md
- VERIFICATION.md
- E2E-PARITY.md
- Backend models and services.
- Inventory and accounting services.
- API views, serializers, and routes.
- Vue pages, components, and router.
- Database migrations.
- Docker configuration.
- CI configuration.
- Existing tests.

The November 11, 2026 completion report recorded:

- 25 complete capabilities.
- 28 partially implemented capabilities.
- 21 missing capabilities.
- 192 backend tests passed in the last recorded full suite.
- 51 browser E2E workflow groups passed.
- Fourteen application entries.

These results are historical evidence. Re-run tests against the current checkout.

## Required audit deliverables

Produce:

1. Complete module inventory.
2. Current architecture diagram.
3. Existing database relationship map.
4. Current API inventory.
5. Frontend page inventory.
6. Feature dependency graph.
7. Security and permissions assessment.
8. Missing feature list.
9. Migration risk assessment.
10. Updated implementation roadmap.

Review the current Git status and establish a reproducible baseline before major refactoring.

---

# 4. ERP CORE PLATFORM

Implement or improve:

- Multi-company management.
- Application registry.
- User management.
- Role-Based Access Control.
- Record-level access rules.
- Company-specific configurations.
- Audit history.
- Activities and reminders.
- Attachments.
- Shared notifications.
- Reusable workflow state handling.
- Document sequence management.
- Currency configuration.
- Localization and translation support.
- Saved filters.
- Reusable list, form, Kanban, calendar, graph, and pivot interfaces.

Backend permissions are mandatory even when frontend controls are hidden.

Verify access controls for every existing and newly implemented application.

---

# 5. CONTACTS AND PRODUCT CATALOG

## Contacts

Complete:

- Parent/child organizations and contacts.
- Invoice and delivery addresses.
- Customer and supplier classifications.
- Duplicate detection.
- Safe contact merging.
- Linked-document history.
- Attachments.
- CSV/XLSX import and export.

## Products

Complete:

- Product templates.
- Product variants.
- Attribute combinations.
- Categories.
- Product images.
- Barcode handling.
- Units of measure.
- Unit conversions.
- Customer pricelists.
- Vendor prices.
- Discounts.
- Product tax settings.
- Costing configuration.

Preserve historical document snapshots when product data changes.

---

# 6. CRM MANAGEMENT

Complete:

- Leads.
- Opportunities.
- Configurable CRM stages.
- Sales teams.
- Opportunity assignment.
- Expected revenue.
- Probability.
- Activities and meetings.
- Follow-up reminders.
- Lost reasons.
- Lead conversion.
- Opportunity-to-quotation integration.
- Pipeline reporting.

Ensure CRM and Sales share the same authoritative customer and quotation records.

---

# 7. SALES MANAGEMENT

Complete the Quote-to-Cash lifecycle.

Features:

1. Quotation management.
2. Quotation templates.
3. Quotation PDF generation.
4. Quotation email workflow.
5. Customer portal access.
6. Customer acceptance and optional signature.
7. Sales order confirmation.
8. Discounts and pricelists.
9. Product availability checks.
10. Stock reservation.
11. Partial delivery.
12. Backorders.
13. Multiple deliveries.
14. Ordered/delivered invoicing policies.
15. Multiple and partial invoices.
16. Sales returns.
17. Credit notes.
18. Refund integration.
19. Sales approval policies.
20. Sales reporting.

## Required business test

A customer orders 10 units.

- Deliver 6.
- Create a backorder for 4.
- Deliver the remaining 4.
- Create valid invoice allocations.
- Receive partial/full payments.
- Return 2 units.
- Generate an approved credit note.
- Process a refund when applicable.

Every quantity and financial balance must reconcile.

---

# 8. PURCHASE MANAGEMENT

Complete:

- Requests for Quotation.
- Supplier pricelists.
- Vendor lead times.
- Approval rules.
- Purchase order confirmation.
- Partial receipts.
- Backorders.
- Supplier returns.
- Replacement receipts.
- Partial vendor bills.
- Three-way matching.
- Vendor credits.
- Supplier refunds.
- Purchase reporting.

Preserve existing partial receipt and replacement return functionality.

---

# 9. INVENTORY MANAGEMENT

Complete:

- Warehouses.
- Hierarchical locations.
- Stock quants.
- Stock reservations.
- Stock availability.
- Stock forecasting.
- Internal transfers.
- Partial deliveries.
- Backorders.
- Lots and serial numbers.
- Expiration dates.
- Barcode scanning.
- Inventory adjustments.
- Customer returns.
- Supplier returns.
- Replenishment rules.
- Stock valuation.
- Inventory reporting.

## Required integrity checks

- No duplicate stock movements.
- No over-reservation.
- No unauthorized negative stock.
- Internal transfers preserve company-wide totals.
- Returns preserve original movement references.
- Stock valuation reconciles according to approved accounting policy.

---

# 10. INVOICING AND PAYMENTS

Complete:

- Customer invoices.
- Vendor bills.
- Standalone invoices.
- Multiple invoices per order.
- Partial invoicing.
- Invoice quantity allocations.
- Payment terms.
- Partial payments.
- Multiple payment allocations.
- Credit notes.
- Refunds.
- Payment reversals.
- Generated PDF documents.
- Invoice email delivery.
- Invoice lifecycle history.

Use immutable posted documents and explicit correction/reversal workflows.

Prevent duplicate financial posting under retries and concurrent requests.

---

# 11. ACCOUNTING MANAGEMENT

Complete:

1. Configurable Chart of Accounts.
2. Sales/Purchase/Bank/Cash/General Journals.
3. Manual Journal Entries.
4. Opening Balances.
5. Customer and Vendor Ledgers.
6. Accounts Receivable.
7. Accounts Payable.
8. Bank Statements.
9. Bank Reconciliation.
10. Tax Configuration.
11. Fiscal Positions.
12. Fiscal Periods and Locks.
13. Credit Note Accounting.
14. Inventory Valuation Integration.
15. Multi-Currency Accounting.
16. Exchange Rate Differences.
17. Analytic Accounts.
18. Cost Centers.
19. General Ledger.
20. Trial Balance.
21. Profit and Loss.
22. Balance Sheet.
23. Cash Flow Reporting.
24. Aging Reports.
25. Financial Statement Exports.

## Accounting requirements

- All posted journal entries must balance.
- Posted financial records are immutable.
- Corrections use traceable reversals.
- Financial reports use authoritative posted entries.
- AR/AP ledgers reconcile to control accounts.
- Inventory valuation follows a documented policy.
- Fiscal periods prevent unauthorized posting.
- Bank reconciliation prevents duplicate matching.

Do not invent statutory tax or accounting rules. Identify and validate the target jurisdiction before localizing.

---

# 12. PROJECT MANAGEMENT

Complete:

- Projects.
- Tasks.
- Configurable task stages.
- Kanban views.
- Milestones.
- Dependencies.
- Scheduling.
- Recurring tasks.
- Team assignments.
- Project activity history.
- Timesheet integration.
- Billable time.
- Project costs.
- Project profitability.
- Project reporting.

Prevent dependency cycles and invalid task transitions.

---

# 13. HUMAN RESOURCES

Complete:

- Employees.
- Departments.
- Reporting hierarchy.
- Private HR records.
- Attendance.
- Working schedules.
- Overtime.
- Leave types.
- Leave allocations.
- Leave approval.
- Recruitment.
- Job applications.
- Interviews.
- Contracts.
- Contract renewal.
- Payroll periods.
- Salary structures.
- Payslips.
- Payroll approvals.
- Payroll accounting.

Payroll must use jurisdiction-validated salary and statutory rules.

Do not expose private HR or compensation data through general employee APIs.

---

# 14. TIMESHEETS

Complete:

- Manual time entries.
- Start/stop timers.
- Project time.
- Task time.
- Helpdesk time.
- Timesheet approval.
- Correction history.
- Billable/nonbillable time.
- Employee cost rates.
- Service billing rates.
- Timesheet-to-invoice allocation.
- Project profitability reporting.

Prevent billing the same approved time twice.

---

# 15. HELPDESK

Complete:

- Support teams.
- Ticket assignments.
- Configurable ticket stages.
- Ticket priorities.
- Customer-linked tickets.
- SLA policies.
- SLA tracking.
- Escalation workflows.
- Internal notes.
- Customer-visible messages.
- Email ticket intake.
- Customer portal.
- Knowledge base.
- Appointments.
- Timesheet integration.
- Helpdesk reporting.

Protect internal notes and customer data from unauthorized portal access.

---

# 16. MANUFACTURING (MRP)

Build a complete Manufacturing module integrated with Inventory, Purchase, and Accounting.

Features:

1. Bill of Materials.
2. BOM Versions.
3. Components.
4. Manufacturing Orders.
5. Manufacturing Work Centers.
6. Work Orders.
7. Production Operations.
8. Component Reservations.
9. Raw Material Consumption.
10. Finished Goods Production.
11. Scrap Management.
12. Production Costing.
13. Manufacturing Scheduling.
14. Manufacturing Reporting.

## Required workflow

BOM → Manufacturing Order → Component Reservation → Production → Finished Goods → Inventory Valuation

Test material consumption, partial production, insufficient stock, scrap, and valuation reconciliation.

---

# 17. POINT OF SALE (POS)

Build a complete POS application.

Features:

- POS Configuration.
- Register Sessions.
- Cashier Authentication.
- Product Catalog.
- Barcode Input.
- Shopping Cart.
- Discounts.
- Tax Calculation.
- Cash Payments.
- Card/External Payment Integration.
- Refunds.
- Receipts.
- Cash Opening and Closing.
- Session Reconciliation.
- Inventory Integration.
- Accounting Integration.
- Offline Operations under an explicitly defined policy.

Test duplicate payments, inventory movements, refunds, and closing-session totals.

---

# 18. WEBSITE AND ECOMMERCE

Implement:

- Public storefront.
- Product catalog.
- Categories.
- Product variants.
- Customer registration/login.
- Shopping cart.
- Checkout.
- Payment integration.
- Delivery address management.
- Customer order history.
- Order tracking.
- Customer portal.
- Returns and refunds.
- eCommerce reporting.

Reuse Sales, Inventory, and Accounting services rather than creating separate duplicate transaction logic.

---

# 19. SUBSCRIPTIONS

Implement:

- Subscription products.
- Recurring plans.
- Subscription contracts.
- Renewal schedules.
- Recurring invoices.
- Proration policy.
- Payment retry workflow.
- Suspension.
- Cancellation.
- Subscription reporting.

Scheduled jobs must be idempotent.

---

# 20. MARKETING AND EVENTS

Implement:

- Contact segments.
- Marketing consent.
- Campaign management.
- Email campaign delivery.
- Automated campaign schedules.
- Campaign performance reporting.
- Events.
- Event registration.
- Attendee management.
- Registration confirmation.

Respect consent, unsubscribe, and applicable privacy requirements.

---

# 21. DOCUMENTS, SIGNATURES AND CUSTOMIZATION

Implement in separate verified milestones:

## Documents

- Document uploads.
- Document folders.
- Permissions.
- Metadata.
- Version history.
- Document search.
- Record attachments.

## Electronic Signatures

- Signature requests.
- Signer authentication.
- Signature status.
- Signature evidence.
- Signed document retention.

Validate legal requirements for the intended jurisdiction.

## Studio-style customization

- Custom fields.
- Custom forms.
- Configurable views.
- Safe field validation.
- Custom workflows.
- Role-protected customization.

Do not dynamically execute arbitrary user-provided code.

---

# 22. ODOO-STYLE USER EXPERIENCE

Create a consistent ERP design system.

Implement:

- Application launcher.
- Top navigation.
- Sidebar navigation.
- Breadcrumbs.
- List views.
- Form views.
- Kanban views.
- Calendar views.
- Pivot views.
- Graph views.
- Status bars.
- Smart buttons.
- Activities.
- Chatter.
- Search.
- Filters.
- Group-by.
- Saved filters.
- Import/export.
- Responsive mobile interface.

Every visible action must have a working implementation.

Preserve KERP branding rather than copying Odoo's proprietary visual assets.

---

# 23. SECURITY

Implement and verify:

- Authentication.
- Secure session management.
- User invitations.
- MFA where selected.
- SSO where selected.
- Configurable roles.
- Model-level permissions.
- Record-level access rules.
- Multi-company isolation.
- API authorization.
- Sensitive field protection.
- Audit history.
- CSRF protection.
- Rate limiting.
- Input validation.
- Secure file uploads.
- Secret management.

Test authorization through direct API requests, not only frontend navigation.

---

# 24. PRODUCTION DEPLOYMENT

Complete:

- Production Django settings.
- Production Vue build.
- HTTPS configuration.
- Secure session cookies.
- Secure CSRF cookies.
- HSTS policy.
- Reverse proxy.
- Production application server.
- Database configuration.
- Worker configuration.
- Static and media hosting.
- Environment secrets.
- Database backups.
- Restore verification.
- Monitoring.
- Error logging.
- Alerts.
- Health checks.
- CI/CD.
- Migration deployment.
- Rollback procedures.
- Load testing.

Do not claim production readiness without verifying an actual deployment environment.

---

# 25. IMPLEMENTATION ORDER

Follow this order, adjusting only when source-code dependencies justify a change.

## Foundation
M0 — Repository Audit and Clean Baseline  
M1 — Core Platform, Permissions, and Shared Services

## Commercial ERP
M2 — Products, Contacts, and Pricing  
M3 — Sales and CRM Completion  
M4 — Inventory Completion  
M5 — Purchase Completion  
M6 — Invoicing, Credit Notes, and Payments  
M7 — Accounting and Inventory Valuation

## Operations
M8 — Project Management  
M9 — Employees and HR  
M10 — Attendance and Leave  
M11 — Recruitment, Contracts, and Payroll  
M12 — Timesheets and Service Billing  
M13 — Helpdesk and Customer Support

## Expansion
M14 — Manufacturing  
M15 — POS  
M16 — Website and eCommerce  
M17 — Subscriptions  
M18 — Marketing and Events  
M19 — Documents and Electronic Signatures  
M20 — Studio-style Customization

## Completion
M21 — Advanced Dashboards and Reporting  
M22 — Security and Performance Verification  
M23 — Production Deployment  
M24 — Full Parity Verification and Release Documentation

Each milestone must include:
- Business requirements.
- Models and migrations.
- Service-layer implementation.
- REST API integration.
- Vue frontend integration.
- Permissions.
- Tests.
- Documentation.
- Acceptance evidence.

Skip already-complete work only after verifying it against the current checkout.

---

# 26. TESTING REQUIREMENTS

For every module:

1. Unit tests.
2. Django API integration tests.
3. Database transaction tests.
4. Concurrency tests where applicable.
5. Company-isolation tests.
6. Role-permission tests.
7. Frontend component tests.
8. Browser E2E tests.
9. Cross-module integration tests.
10. Regression tests.

Critical business invariants:

- No duplicate stock deductions.
- No over-reservation.
- No duplicate invoice postings.
- Every posted journal balances.
- No unauthorized cross-company access.
- No duplicate payroll posting.
- No duplicate POS payment settlement.
- No duplicate subscription billing.
- No corrupted historical document references.

Tests must use realistic fixtures and report exact pass/fail results.

---

# 27. DEFINITION OF DONE

Mark a capability complete only if:

- Business workflow works.
- Backend logic exists.
- Database model and migrations are valid.
- API is functioning.
- Vue interface is functioning.
- Authorization is enforced.
- Cross-company isolation is verified.
- Relevant edge cases are tested.
- Regression tests pass.
- Documentation is updated.
- Acceptance evidence is recorded.

A module with a working menu icon or CRUD page is not necessarily complete.

---

# 28. AUTOMATIC CONTINUATION INSTRUCTIONS

Work through the roadmap in dependency order without repeatedly asking which milestone to implement next.

For each milestone:

1. Inspect current source code.
2. Produce a concise implementation plan.
3. Implement the required models and services.
4. Create migrations.
5. Implement or update API routes.
6. Build frontend interfaces.
7. Add tests.
8. Execute verification commands.
9. Fix discovered issues.
10. Update the parity matrix.
11. Record completion evidence.
12. Move to the next eligible milestone when possible.

Continue only while the current execution environment and authorization permit.

If execution limits, unavailable integrations, required secrets, or major unresolved design decisions block progress, record the exact blocker and remaining work. Do not pretend to continue working after the session ends.

Do not deploy production changes, process real payments, send external messages, or perform destructive data operations without the necessary authorization.

---

# 29. REQUIRED REPORT AFTER EVERY MILESTONE

Use this structure:

## KERP Milestone Completion Report

**Milestone:**  
**Current Git Commit:**  
**Implementation Status:**  

### Implemented Features
Describe completed business behavior.

### Backend Changes
List modified source files, services, and models.

### Database Changes
List migrations and reconciliation outcomes.

### API Changes
Document added or modified endpoints.

### Frontend Changes
Describe Vue pages and components.

### Tests
Include exact commands and actual results.

### Security
Show permission and company-isolation verification.

### Business Acceptance
Provide input, expected output, and actual output.

### Remaining Issues
List incomplete or defective functionality.

### Updated Documentation
Identify changed documentation files.

### Next Milestone
State the next dependency-ready milestone.

Do not claim completion without supporting evidence.

---

# 30. FINAL PROJECT ACCEPTANCE

The KERP project may be declared complete for its agreed scope only after:

1. All selected feature acceptance criteria pass.
2. Every required ERP workflow has real backend and frontend functionality.
3. Cross-module business transactions reconcile.
4. Financial postings are balanced and auditable.
5. Inventory valuation is reconciled.
6. Role-based and company-level permissions pass security tests.
7. Automated regression suites pass.
8. Production deployment is verified.
9. Backup restoration is tested.
10. Known limitations are documented.
11. The parity matrix contains current verified evidence.
12. Any claimed Odoo parity is supported by reproducible comparison tests for the selected edition, applications, and jurisdiction.

Do not present 100% Odoo parity as achieved solely from the current 74-item checklist.

---

# BEGIN IMPLEMENTATION

Start immediately by auditing the existing KERP repository.

Do not rebuild working modules.

Identify the current implementation state, compare it with the roadmap, and implement the highest-priority unfinished milestone.

Prioritize transactional integrity across Sales, Inventory, Purchase, Invoicing, and Accounting.

After each verified milestone, update the project completion report and proceed to the next eligible milestone within the current execution session.

**Final objective: Deliver a complete, secure, integrated, tested, and production-ready KERP ERP platform following the selected Odoo 19 Community and Enterprise business concepts.**