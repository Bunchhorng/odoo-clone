# UI-00 — Frontend architecture and UX audit

Audit date: 2026-11-15. This is an implementation-facing audit of the current
Vue source. It does not represent an independent visual-design review in a
browser; the verification section records the checks run for this milestone.

## Current architecture

The frontend is a Vue 3/Vite single-page application. `App.vue` renders the
permission-aware `ERPAppShell`, which owns the top navigation, app launcher,
company context, account menu, breadcrumbs, module tabs, API-health feedback,
and mobile header behavior. Vue Router owns public account routes and protected
application routes. Pinia's auth store restores the server session and provides
the active company/role to the shell and pages. API authorization remains a
backend responsibility; the navigation only avoids presenting unavailable work.

Shared UI is intentionally component-led:

| Area | Existing implementation |
| --- | --- |
| Application navigation | `ERPAppShell`, `ERPAppLauncher`, `ERPPopover`, `ERPCompanySwitcher` |
| Lists and records | `ERPListView`, `ERPDataTable`, `ERPFormView`, `ERPKanbanView`, `UiPagination` |
| Workflow feedback | `ERPStatusBar`, `ERPNotificationCenter`, `ERPModal`, notices and empty states |
| Visual foundation | `tokens.css`, `main.css`, `workspace.css`, `components.css`, `erp.css` |

The implemented route inventory covers Dashboard, Contacts, CRM, Sales,
Purchase, Inventory (products, movements, warehouses, locations), Invoicing,
Accounting, Projects, Tasks, Employees, Timesheets, Helpdesk, Team, Companies,
Settings, account security, and the setup guide. Public routes include sign in,
registration, forgotten-password, and reset-password flows.

## Findings and delivery order

1. **UI-01 — global theme:** a usable semantic token system, focus treatment,
   dialog/list primitives, dark mode, responsive rules, and accessible shell
   already existed. This milestone removes remaining hard-coded dashboard and
   card colors in favour of theme-aware workflow tokens. It deliberately keeps
   KERP branding and does not copy Odoo assets.
2. **UI-02 — app launcher and navigation:** substantially implemented. The
   launcher filters applications, has keyboard access, respects visible role
   restrictions, and presents unavailable apps as non-links. Continue to keep
   backend permissions authoritative.
3. **UI-03 — reusable application pages:** list, table, form, modal, kanban,
   status, and empty-state components are available. New modules should use
   these before adding page-specific controls.
4. **UI-04 onward — module workflows:** incrementally migrate the remaining
   page-specific layouts to shared components as their business workflows are
   implemented and tested. Do not use a cosmetic rewrite to mask incomplete
   business functionality.

## Accessibility and responsive observations

- Global visible-focus styles, reduced-width layout rules, skip link, labelled
  scrollable tables, modal focus handling, status/live-region messages, and
  keyboard-operable app/popover controls are present.
- Tables and kanban lanes intentionally scroll horizontally at narrow widths;
  the surrounding pages constrain their width. The existing browser suite checks
  1440px through 320px and scans for accidental overflow.
- Token contrast is automatically checked for light and dark themes. The audit
  found no confirmed nonfunctional action in the inspected shared components.
- There are still five CSS layers, including legacy module rules in `erp.css`.
  Further work should reduce that legacy surface gradually, after visual and
  workflow tests identify the exact page to change.

## UI-01 implementation

`tokens.css` now defines semantic progress and activity-marker colors for both
themes. `erp.css` consumes them for the dashboard pipeline and activity stream,
and card/document shadows use the shared shadow token. This makes light/dark
theme changes coherent without changing workflow data, routes, permissions, or
business APIs.

## Verification plan

Run the following from `frontend` after UI changes:

```powershell
npm run typecheck
npm run lint
npm run test
npm run build
npm run test:e2e
```

The E2E suite requires the local frontend, backend, and Docker-backed test
environment described in `tests/e2e/workspace.spec.ts`. Its coverage includes
launcher keyboard behavior, core application navigation, forms, role-sensitive
controls, modal focus management, multiple viewport sizes, API health, and
accessibility checks.

### UI-01 local evidence (2026-11-15)

- `npm run typecheck`: passed.
- `npm run lint`: passed with zero warnings.
- `npm run test`: passed — 4 files and 46 tests.
- `npm run build`: passed — 110 modules transformed.
- `npm run test:e2e`: started 18 Playwright tests; the launcher/navigation and
  form modal-focus workflows passed. The local runner did not emit a final JSON
  report, so the remaining browser tests are intentionally **not** marked as
  passed and should be rerun from a normal local terminal before closing a
  broader UI milestone.
