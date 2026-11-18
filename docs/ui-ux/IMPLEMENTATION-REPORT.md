# KERP frontend implementation report

## 1. Problems identified

Conflicting global CSS, low-contrast launcher text, redundant navigation, unguarded
app-menu dismissal, missing dark theme, unclear company/app availability, an
overstated API health message and missing frontend verification tooling. The
source-level [audit](AUDIT.md) records findings and their resolutions.

## 2. Components changed

Added all requested shared ERP components: AppLauncher, AppShell, ListView,
FormView, KanbanView, SearchBar, FilterMenu, GroupByMenu, StatusBar, DataTable,
Modal, Chatter, CompanySwitcher and NotificationCenter, with the `ERP` prefix.
Added a shared popover and theme composable. Existing `UiDialog` and `RecordTable`
now adapt to the shared implementations; `AppIcon` retains existing icons and adds
shell controls. CatalogToolbar and catalog/document/dashboard integrations reuse
the new primitives. Details: [component contracts](DESIGN-SYSTEM.md).

## 3. Routes affected

Every page uses the new shell, tokens and appearance preference. No route paths
change. Shared view integrations cover Contacts, Products, CRM, Projects, Tasks,
Employees and Departments. Sales, Purchase and Invoicing use shared status
presentation; Invoicing uses the shared payment modal; Dashboard uses shared
activity rendering. Central module menus replace copies in catalog, stock,
sales/purchase, invoice, timesheet and settings screens.

## 4. API integration changes

No backend contract or endpoint changes. Existing Django sessions, CSRF headers,
current-user/company data, company-selection POSTs and server authorization are
retained. A typed registry adapter follows existing company membership rules.
The activity control requests the real dashboard activity on demand. The API
client now rejects unexpected successful non-JSON responses. Initial rendering
waits for session-aware routing; session refresh errors are shown with retry.

## 5. Screens improved

The launcher has consistent cards/icons/descriptions, task/name search, keyboard
shortcut, visible focus and company-aware unavailable states. All screens gain
the compact shell, account/appearance menu and company context. Catalog list,
form and Kanban layouts retain real actions. Wide module tables receive named
keyboard scroll targets; payment history is contained; mobile service-filter
labels wrap. Light/dark palettes use tested semantic contrast pairs.

## 6. Tests executed

Vue type checking, ESLint, 44 Vitest checks, production build and 177 existing
Django tests passed. Playwright and the existing business regression workflow are
also executed against the local stack; their final results, evidence paths and
scope are recorded in [UI-VERIFICATION.md](../testing/UI-VERIFICATION.md).
The frontend quality gate is wired into the existing check script and CI.

## 7. Remaining issues and limits

The backend has no per-app entitlements or unread/read notification API. The
activity center displays real events without unread counters; chatter is read-only.
Grouping applies to the current page. Legacy business views remain JavaScript,
and specialized document/service views retain their working domain-specific
logic. Manual browser-toolbar zoom, screen-reader and forced-color checks plus
Firefox/WebKit coverage remain outstanding. Automated zoom coverage checks the
equivalent CSS reflow, not the browser toolbar.

## 8. Recommended next milestone

Incrementally type API response models and extend the shared form/list patterns
through specialized document/service screens. Add cross-browser and manual
accessibility validation. Define server-owned app entitlements and real
notification lifecycle contracts only if those product capabilities are needed.
Review groups and contributor guidance are in
[UI-WORKFLOW.md](../teamManagement/UI-WORKFLOW.md).

Existing dirty business-module work was preserved. No commits or deployments
were created by this task; changes remain in the local checkout for review.
