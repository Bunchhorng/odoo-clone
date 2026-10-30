# KERP design system

The interface keeps KERP branding and uses familiar ERP patterns: a compact purple
header, app switcher, company context, module navigation, control panels and data
views. Source inspection and decisions are in [AUDIT.md](AUDIT.md).

## Tokens and ownership

`frontend/src/assets/tokens.css` owns semantic colors, font sizes, spacing, radius,
shadows and focus colors. `data-theme="light|dark"` selects the palette. Appearance
offers System, Light and Dark; only this preference is saved in local storage.
Authentication and company selection remain in the Django session.

| Token group | Use |
| --- | --- |
| `primary`, `primary-hover`, `on-primary` | Actions and selection |
| `background`, `surface`, `surface-subtle`, `surface-hover` | Canvas, panels and interaction states |
| `text`, `text-muted`, `text-soft`, `link` | Readable copy, supporting copy, placeholders and links |
| `border`, `input-border`, `focus` | Separators, recognizable controls and keyboard focus |
| `success`, `warning`, `danger`, `info` and matching `-bg` tokens | Feedback with text and color |
| `font-xs` through `font-lg`, `font-sans` | 12px default supporting text, system fonts, larger headings |
| `space-1` through `space-7` | 4/8/12/16/24/32/48px spacing scale |
| `radius-sm/md/lg/pill`, `shadow-sm/menu/modal` | Controls, panels, menus and dialogs |

Text token pairs are automatically checked at 4.5:1; input boundaries and focus
colors are checked at 3:1. App accent colors are decorative borders, not the sole
indication of app identity. Automated scans supplement these checks; they do not
certify every possible module, data set or assistive technology.

`main.css` owns foundations/account layouts, `erp.css` retains module layouts,
`components.css` contains catalog/service extensions, and `workspace.css` owns the
shell/launcher. Tailwind utilities are enabled without Preflight to preserve
working table/form defaults; its semantic colors reference the same tokens.

## Shared components

All ERP components live in `frontend/src/components/erp/`. New primitives use
TypeScript. Existing JavaScript views remain supported through `allowJs`; this is
an incremental migration, not full typing of the legacy application.

| Component | Contract / integration |
| --- | --- |
| `ERPAppShell` | Session-aware header, app switcher, centrally defined module menus, breadcrumbs, account/appearance, company context and real activity |
| `ERPAppLauncher` | `apps`, `loading`, `error`; `retry`; trimmed name/description search, company gating, role filtering, unavailable states |
| `ERPListView` | `loading`, `error`, `empty`, `hasCompany`, `title`; `retry`; feedback/default/empty slots; suppresses stale data |
| `ERPFormView` | `busy`, `error`, `readonly`; `submit`; field/context/action slots; no internal persistence |
| `ERPKanbanView` | `stages`, `rows`, `title`, `canCreate`, `busy`; `create`, `drop`; card/column-header slots; existing keyboard stage selectors retained |
| `ERPSearchBar` | `v-model`, `label`, `placeholder`, `disabled`; `search`; clear button, Escape and exposed `focus()` |
| `ERPFilterMenu` | Native keyboard disclosure; filter slot; open by default to preserve existing workflows |
| `ERPGroupByMenu` | `v-model`, `options`, `disabled`; explicitly groups the current page, not the server's entire result set |
| `ERPStatusBar` | `value`, `steps`, `label`; descriptive status only; business transitions remain explicit API actions |
| `ERPDataTable` | Columns/rows, sorting events, page selection, named cell/action slots and optional current-page grouping; named focusable scroll region |
| `ERPModal` | `title`, `busy`, `beforeClose`; `closed`; exposed `showModal/close`; native modal containment, guarded Escape, focus wrapping/return |
| `ERPChatter` | Real activity array, loading/error/retry; intentionally read-only; no fabricated message composer |
| `ERPCompanySwitcher` | Calls existing company-selection POST; honors dirty-form guards; restores selection on failure |
| `ERPNotificationCenter` | Fetches real `dashboard/` activity on demand; no unread/read/dismiss actions without a notification API |
| `ERPPopover` | Reusable disclosure; Escape/outside-click/route dismissal; arrow/Home/End movement; Tab follows document order |

`UiDialog` and `RecordTable` are compatibility adapters so existing callers retain
their props, events, exposed methods and named slots. Catalog forms and queries
continue to use their existing validation, dirty guards, pagination and APIs.

## Routes and availability

`data/apps.ts` adapts the existing module registry. All 14 routed applications have
implemented features, so none is falsely marked Coming soon. A future unfinished
app can use `status: 'coming-soon'`, producing a non-actionable tile. Applications
requiring business context remain disabled until a company is selected.

Current authorization is company membership with owner/admin/member roles. The
backend has no finer app-entitlement contract. Members retain existing read access
and supported self-service actions; manager-only writes stay guarded in existing
views and on the server. Optional registry role restrictions must match backend
policy before use.

The shared shell affects every route. Catalog/List/Form/Kanban changes affect
`/contacts`, `/inventory`, `/crm`, `/projects`, `/tasks`, `/employees` and
`/employees/departments`. Central menus replace copied tabs in those screens plus
stock, sales, purchase, invoices, timesheets and settings. Sales/purchase/invoices
use the shared status display; dashboard uses shared activity rendering. No route
paths or backend contracts change.

## Keyboard and responsive behavior

Use Tab/Shift+Tab for ordinary navigation, Enter/Space for disclosures, Escape to
close a popover and return to its trigger, and arrows/Home/End inside disclosures.
On the launcher, `/` focuses app search outside editable fields. Native company
selection remains available to screen readers. Dialog Escape honors busy/dirty
guards. Boards retain explicit stage selectors as an alternative to drag/drop.

Grids change from four columns to three, then two; descriptions remain visible at
320px. Module tabs and wide tables/boards scroll within their containers. Menus
fit the mobile viewport. Reduced-motion preferences disable transitions.

Implementation references: [Vue TypeScript](https://vuejs.org/guide/typescript/overview.html),
[Tailwind Vite integration](https://tailwindcss.com/docs/installation/using-vite),
[Vue ESLint](https://eslint.vuejs.org/user-guide/),
[Vitest](https://vitest.dev/guide/) and
[Playwright configuration](https://playwright.dev/docs/test-configuration).
