# KERP — Prompt 10: Complete Odoo 19-Style ERP Frontend UI/UX Redesign

## ROLE

Act as a Senior ERP UI/UX Designer, Odoo 19 Functional Consultant, Senior Vue.js Frontend Engineer, Frontend Architect, Accessibility Specialist, and QA Automation Engineer.

You are responsible for redesigning the entire existing KERP application interface to follow Odoo 19 Community and Enterprise user interface concepts and interaction patterns.

Your task is to inspect the existing frontend, create a reusable ERP design system, improve every implemented application, and verify all workflows.

Do not simply provide suggestions or mockups. Implement the frontend improvements in the existing repository.

---

# 1. PROJECT INFORMATION

Project: KERP

Technology:
- Frontend: Vue.js
- Backend: Django
- Database: MySQL
- Infrastructure: Docker Compose

Reference:
- Odoo 19 Community UI concepts
- Odoo 19 Enterprise UI concepts
- Official Odoo 19 user documentation

## MAIN OBJECTIVE

Transform KERP into a modern, professional ERP application with a coherent Odoo-style interface.

Match the interaction concepts and information architecture of Odoo 19 as closely as practical, while preserving KERP branding and avoiding unauthorized copying of Odoo proprietary assets.

The finished interface must be:

- Clean and professional.
- Consistent across applications.
- Easy to navigate.
- Responsive on desktop, tablet, and mobile.
- Accessible.
- Connected to real backend functionality.
- Suitable for business users.
- Reusable and maintainable.

Do not rewrite the Django backend or database merely for visual changes.

---

# 2. MANDATORY RULES

1. Inspect the existing KERP Vue frontend before coding.
2. Identify current layouts, routes, components, styling, and dependencies.
3. Preserve working functionality.
4. Preserve current authentication and API integrations.
5. Do not change business logic unnecessarily.
6. Do not introduce new API requirements without documenting them.
7. Use reusable Vue components.
8. Avoid duplicated CSS and components.
9. Do not create nonfunctional buttons.
10. Do not hide features currently available to authorized users.
11. Keep permission-aware navigation.
12. Preserve unsaved form changes and draft data.
13. Support loading, empty, error, and success states.
14. Implement responsive layouts.
15. Support keyboard navigation and accessible labels.
16. Test every modified critical workflow.
17. Do not copy Odoo trademarks, logos, proprietary icons, or protected assets.
18. Update frontend documentation.
19. Do not claim complete Odoo UI parity without verified comparisons.
20. Implement incrementally and run regression tests after each major change.

---

# 3. PHASE 1 — FRONTEND AUDIT

Inspect:

- `frontend/src/`
- Existing router configuration.
- Existing layout components.
- Existing navigation and sidebar.
- Existing application launcher.
- Existing dashboard.
- Existing tables and forms.
- Existing UI components.
- Existing styling system.
- Existing permission-aware navigation.
- Existing API clients and state management.
- Existing frontend tests.
- Existing browser E2E tests.

Also read:

- ROADMAP.md
- ODOO-PARITY-MATRIX.md
- VERIFICATION.md

## REQUIRED OUTPUT

Produce:

1. Existing UI architecture.
2. Complete page inventory.
3. Component inventory.
4. Inconsistent styling report.
5. Navigation problems.
6. Responsive layout issues.
7. Accessibility issues.
8. Broken or nonfunctional UI actions.
9. Reusable component opportunities.
10. Implementation order.

Do not start a broad redesign until the current behavior has been mapped.

---

# 4. PHASE 2 — GLOBAL DESIGN SYSTEM

Create a centralized KERP design system inspired by Odoo 19.

## Design direction

Use a professional, minimal ERP appearance with:

- Light neutral backgrounds.
- White or near-white content surfaces.
- Subtle borders.
- Consistent spacing.
- Compact but readable business tables.
- Clear page titles.
- Reserved accent colors.
- Professional iconography.
- Consistent forms and dialogs.

Suggested KERP theme tokens:

Primary: #714B67  
Primary Hover: #5B3A53  
Secondary Accent: #017E84  
Page Background: #F7F8FA  
Surface: #FFFFFF  
Text Primary: #202124  
Text Secondary: #64748B  
Border: #E5E7EB  
Success: #16A34A  
Warning: #D97706  
Danger: #DC2626

These are suggested visual tokens, not a requirement to copy Odoo's exact theme.

Use CSS variables or existing theme utilities.

Support consistent:
- Colors.
- Typography.
- Spacing.
- Border radius.
- Shadows.
- Focus states.
- Table density.
- Form controls.
- Buttons.
- Status colors.
- Dialogs.
- Toast notifications.

If dark mode exists, preserve and improve it.

Do not introduce dark mode if it would delay critical UI consistency without an explicit project requirement.

---

# 5. PHASE 3 — APP LAUNCHER

Implement an Odoo-style application launcher.

## Requirements

Display installed and authorized application entries:

- Dashboard
- Contacts
- CRM
- Sales
- Purchase
- Inventory
- Invoicing
- Accounting
- Projects
- Employees
- Attendance
- Leave
- Timesheets
- Helpdesk
- Manufacturing
- POS
- eCommerce
- Settings

Show only implemented, accessible modules.

For incomplete applications, use a clearly labeled development state instead of a fake functional app.

## Features

- Application grid.
- Application icons.
- Search applications.
- Recently used applications.
- Favorites where supported.
- Role-aware visibility.
- Keyboard navigation.
- Responsive grid.

## Acceptance

- Clicking an authorized app opens the correct route.
- Search filters applications correctly.
- Unauthorized apps are not exposed as accessible routes.
- Launcher works on desktop and mobile.

---

# 6. PHASE 4 — MAIN NAVIGATION

Implement a consistent global navigation system.

## Top Navigation

Include:

- KERP application identity.
- Current application name.
- Application navigation.
- Global search where supported.
- Activities/notifications where supported.
- Company switcher.
- User profile menu.

## Navigation behavior

- Active route highlighting.
- Back navigation.
- Breadcrumbs.
- Responsive mobile navigation.
- Keyboard access.
- Correct company-switch behavior.
- No duplicate or conflicting navigation systems.

Use a consistent design across every ERP application.

---

# 7. PHASE 5 — ODOO-STYLE LIST VIEW

Create a reusable ListView component.

## Features

- Table headers.
- Sortable columns.
- Search.
- Filters.
- Group By.
- Saved Favorites.
- Pagination.
- Selectable rows.
- Bulk actions.
- Row actions.
- Status badges.
- Export where supported.
- Empty states.
- Loading states.
- Permission-aware actions.

## Example

Sales Orders List:

Columns:
- Order Number
- Customer
- Order Date
- Salesperson
- Total
- Delivery Status
- Invoice Status
- Order Status

## Acceptance

- Search works through real data.
- Filtering and sorting work correctly.
- Pagination preserves active filters.
- Selected-row actions enforce permissions.
- Tables work on smaller screens.
- Bulk actions handle partial failures.

Avoid using client-side filtering as a substitute for server pagination when datasets are large.

---

# 8. PHASE 6 — ODOO-STYLE FORM VIEW

Create a reusable ERP form layout.

## Header

Include:

- Record title/reference.
- Primary action buttons.
- Status bar.
- Create/Edit actions according to permissions.
- Save/Discard behavior.
- More Actions menu.

## Body

Include:

- Main business information.
- Organized field groups.
- Related record links.
- Smart buttons.
- Notebook-style tabs.
- Notes.
- Attachments.
- Activities.
- Record history.

## Example: Sales Order

Header:
- Confirm
- Send
- Print
- Cancel
- Status

Smart Buttons:
- Deliveries
- Invoices
- Payments

Tabs:
- Order Lines
- Other Information
- Notes

## Acceptance

- Actions call real backend APIs.
- Server validation errors display beside the relevant fields.
- Dirty-form guards prevent accidental data loss.
- Confirmed/posted records respect read-only rules.
- Related document buttons navigate correctly.

---

# 9. PHASE 7 — KANBAN VIEW

Implement a reusable Kanban component.

Use it for:

- CRM opportunities.
- Project tasks.
- Recruitment applications.
- Helpdesk tickets.
- Other stage-based workflows.

## Features

- Configurable columns.
- Card counters.
- Card details.
- Priority indicators.
- Assigned users.
- Activity indicators.
- Drag-and-drop where permitted.
- Optimistic updates with rollback.
- Keyboard-accessible alternatives.

Do not allow arbitrary state changes.

The backend must validate all transitions.

---

# 10. PHASE 8 — CALENDAR VIEW

Implement calendar experiences for:

- Activities.
- Meetings.
- Project deadlines.
- Leave requests.
- Attendance schedules.
- Appointments.

Support:

- Month view.
- Week view.
- Day view.
- Event details.
- Timezone handling.
- Date navigation.
- Filters.
- Authorized event creation/editing.

Avoid duplicating the same appointment or activity data in separate incompatible calendars.

---

# 11. PHASE 9 — SMART BUTTONS

Implement reusable smart buttons for related records.

Examples:

Sales Order:
- Deliveries
- Invoices
- Payments

Purchase Order:
- Receipts
- Vendor Bills

Product:
- On Hand
- Forecasted
- Movements

Customer:
- Opportunities
- Sales
- Invoices

Employee:
- Attendance
- Leave
- Timesheets

Project:
- Tasks
- Timesheets
- Invoices

## Requirements

- Display accurate related-document counts.
- Navigate to filtered related records.
- Enforce user permissions.
- Avoid expensive unnecessary requests.
- Use consistent visual placement.

---

# 12. PHASE 10 — ACTIVITIES AND CHATTER

Implement Odoo-style record activity and history components using KERP's own data structures.

## Activity component

Support:

- Activity type.
- Assigned user.
- Deadline.
- Completion.
- Status.
- Related record.

## Record history

Show:

- Business events.
- Status changes.
- Approved field changes.
- Notes.
- Attachments.
- Authorized messages.

Separate private audit information from customer-visible comments.

If backend activity/chatter endpoints are missing, document the dependency instead of inventing frontend-only records.

---

# 13. PHASE 11 — DASHBOARD REDESIGN

Create application-specific dashboards.

## Main Dashboard

Show authorized company metrics and app shortcuts.

## Sales Dashboard

- Quotations.
- Confirmed orders.
- Pending delivery.
- To invoice.
- Sales trend.

## Inventory Dashboard

- Receipts.
- Deliveries.
- Transfers.
- Low stock.
- Backorders.

## Accounting Dashboard

- Customer invoices.
- Vendor bills.
- Receivables.
- Payables.
- Bank reconciliation status.

## HR Dashboard

- Employees.
- Attendance.
- Leave approvals.
- Contract alerts.

## Helpdesk Dashboard

- Open tickets.
- Assigned tickets.
- SLA risk.
- Resolution performance.

Use real APIs.

Do not use fake static business figures in production interfaces.

---

# 14. PHASE 12 — REPORTING VIEWS

Implement:

- Pivot tables.
- Graph view.
- Bar charts.
- Line charts.
- Date filters.
- Comparison periods.
- Drill-down navigation.
- Saved reports.
- Export actions.

Reuse the authorized reporting APIs.

Never calculate accounting revenue from unrelated frontend totals.

---

# 15. PHASE 13 — REDESIGN ALL IMPLEMENTED MODULES

Apply the shared UI components systematically.

## Core Modules

1. Dashboard
2. Contacts
3. Products
4. CRM
5. Sales
6. Purchase
7. Inventory
8. Invoicing
9. Accounting
10. Projects
11. Employees
12. Timesheets
13. Helpdesk
14. Settings

Also redesign additional modules that exist in the current repository, such as Attendance, Leave, Recruitment, Payroll, Manufacturing, POS, eCommerce, Subscriptions, Marketing, and Documents.

Do not assume every future module has already been implemented.

For every module:

- Review the existing page.
- Identify relevant Odoo-style view patterns.
- Reuse design-system components.
- Preserve API behavior.
- Improve layout and spacing.
- Improve forms.
- Improve table actions.
- Improve responsive behavior.
- Verify navigation.
- Test critical workflows.

Do not change every page simultaneously.

Complete one module group and verify it before proceeding.

---

# 16. PHASE 14 — RESPONSIVE MOBILE UI

Support practical desktop, tablet, and mobile workflows.

## Desktop

- Full ERP navigation.
- Dense tables.
- Multi-column forms.
- Smart buttons.
- Reporting views.

## Tablet

- Adaptive navigation.
- Reduced columns.
- Responsive forms.

## Mobile

- Compact application navigation.
- Accessible action menus.
- Readable forms.
- Card/list alternatives for wide tables.
- Responsive dialogs.
- No horizontal page overflow.

Do not hide essential business actions on mobile.

---

# 17. PHASE 15 — REUSABLE COMPONENT ARCHITECTURE

Inspect existing components and create only missing reusable abstractions.

Suggested structure:

frontend/src/

components/
  erp/
    AppLauncher.vue
    AppNavbar.vue
    Breadcrumbs.vue
    PageHeader.vue
    SearchBar.vue
    FilterDropdown.vue
    GroupByMenu.vue
    ListView.vue
    FormView.vue
    KanbanView.vue
    CalendarView.vue
    StatusBar.vue
    SmartButton.vue
    ActivityPanel.vue
    ChatterPanel.vue
    FormField.vue
    MoneyField.vue
    QuantityField.vue
    DateField.vue
    StatusBadge.vue
    ConfirmDialog.vue
    EmptyState.vue
    LoadingState.vue
    ErrorState.vue

layouts/
  ERPLayout.vue
  AuthLayout.vue

composables/
  usePermissions.js
  useCompany.js
  useFilters.js
  usePagination.js
  useFormState.js

styles/
  tokens.css
  components.css

Adapt to existing Vue conventions, routing, TypeScript/JavaScript choices, and styling architecture.

Do not introduce duplicate libraries if equivalent dependencies are already installed.

---

# 18. PHASE 16 — TESTING AND QUALITY

Add frontend component and E2E tests.

Required checks:

1. App launcher opens the correct module.
2. Unauthorized modules remain inaccessible.
3. Navigation highlights active routes.
4. Company switching refreshes scoped data.
5. List filters work.
6. Sorting works.
7. Pagination works.
8. Forms validate correctly.
9. Unsaved changes trigger a warning.
10. Smart buttons navigate correctly.
11. Kanban transitions are validated.
12. Actions display successful/error responses.
13. Reports display actual API data.
14. Mobile forms remain usable.
15. Dialogs support keyboard navigation.
16. No unexpected console errors.
17. No broken critical routes.
18. Existing business workflows remain functional.

Run the existing browser and backend integration tests after changes.

Record screenshots at representative desktop, tablet, and mobile viewport sizes.

---

# 19. VISUAL QUALITY REQUIREMENTS

Evaluate each redesigned page against these criteria:

- Clear information hierarchy.
- Consistent typography.
- Consistent margins and padding.
- Appropriate content density.
- Consistent button hierarchy.
- Readable tables.
- Clear status differentiation.
- Proper field alignment.
- Accessible contrast.
- Predictable navigation.
- Correct error messages.
- Responsive layouts.

Avoid:

- Excessive dashboard cards.
- Oversized empty spaces.
- Inconsistent button styles.
- Decorative icons without meaning.
- Duplicated sidebars.
- Conflicting colors.
- Tiny unreadable tables.
- Fake workflow states.
- Broken mobile layouts.

Favor practical ERP usability over decorative effects.

---

# 20. IMPLEMENTATION MILESTONES

Follow this order:

UI-00 — Existing UI Audit

UI-01 — Global Theme and Design Tokens

UI-02 — App Launcher and Main Navigation

UI-03 — Reusable List View

UI-04 — Reusable Form View and Status Bar

UI-05 — Smart Buttons and Related Documents

UI-06 — Kanban and Calendar

UI-07 — Activities, Chatter, and Attachments

UI-08 — Sales, Purchase, and CRM Redesign

UI-09 — Inventory, Products, and Contacts Redesign

UI-10 — Invoicing and Accounting Redesign

UI-11 — Projects, Employees, Timesheets, and Helpdesk Redesign

UI-12 — Settings and User Management

UI-13 — Additional Implemented ERP Applications

UI-14 — Dashboards, Graphs, and Pivot Views

UI-15 — Mobile Responsive Improvements

UI-16 — Accessibility and Visual Regression Tests

UI-17 — Full Frontend Verification

After every milestone, update the progress report and verify affected workflows.

---

# 21. PROOF OF IMPLEMENTATION

After every UI milestone, provide:

1. Exact Vue files changed.
2. Components created or reused.
3. Existing routes preserved.
4. API integrations verified.
5. Screenshots before/after where available.
6. Responsive screenshots.
7. Accessibility findings.
8. Test commands and actual results.
9. Remaining visual or functional defects.
10. Documentation changes.

Classify the milestone:

- Complete within defined scope.
- Partially complete.
- Missing.
- Defective.

Never mark a milestone complete solely because a screenshot looks attractive.

---

# 22. FIRST ASSIGNMENT

Begin with:

**UI-00 — Existing KERP Frontend Audit**

1. Inspect frontend architecture.
2. Identify all implemented pages and layouts.
3. List existing reusable components.
4. Analyze current navigation.
5. Compare UI patterns against Odoo 19 concepts.
6. Identify inconsistent styles.
7. Identify responsiveness issues.
8. Find broken buttons and navigation.
9. Create a dependency-aware redesign plan.
10. Record the baseline frontend build and E2E test results.

Then implement:

**UI-01 — Global Theme and Design Tokens**

- Create or consolidate shared design tokens.
- Normalize typography, spacing, buttons, inputs, and status colors.
- Preserve existing features and data.
- Verify all affected pages.
- Run the frontend build and relevant tests.

Continue into subsequent milestones in order when dependencies and verification permit.

Do not begin a broad redesign that breaks existing business workflows.

## FINAL OBJECTIVE

Deliver a complete, consistent, professional, responsive, and verified **KERP ERP frontend inspired by Odoo 19 Community and Enterprise**.

Every implemented module should feel like part of one integrated ERP application, with consistent navigation, forms, lists, Kanban views, activities, smart buttons, and reporting.

The UI must be functional, not just visually similar to Odoo.