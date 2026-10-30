# KERP interface audit — 30 October 2026

Audit baseline: the existing Vue 3/Pinia/Vite JavaScript frontend and Django JSON
APIs, including the business-module changes already present in the checkout.
Those changes are retained. This is an incremental interface update, not a rewrite.

| Area | Finding | Resolution in this change |
| --- | --- | --- |
| Design | Three stylesheets redefine the same root, typography, shell and controls; green, teal and purple themes conflict. | Central semantic tokens; retain module layouts, remove superseded shell/launcher rules. |
| Contrast | Translucent launcher descriptions, 9–11px navigation/status text and muted table labels are hard to read. | Opaque surfaces, AA text pairs, readable type and visible focus. |
| Launcher | Static tiles ignore company context, descriptions disappear on mobile, no explicit availability model. | Shared app registry, session/company-aware access, consistent responsive cards, clear disabled/loading/error/search states. |
| Navigation | Global Apps/Companies/Team links duplicate the app dropdown; module tabs are copied between views. | Reusable shell, one app switcher, centrally defined module navigation, breadcrumbs and account dropdown. |
| Keyboard | Native details menu stays open; no Escape/outside-click handling, no menu focus movement. | Shared disclosure with Escape, arrow/Home/End controls, focus return and outside-click/route dismissal. |
| Health | “Your workspace is ready” claims business readiness from a health/database probe. | Explicit API/database connectivity status; each module keeps its own loading/error handling. |
| Themes | No dark theme; many hardcoded surfaces and text colors. | Persisted system/light/dark preference, semantic styles across existing screens. |
| Tables/boards | Horizontal scrolling lacks a named keyboard focus target. | Named, focusable scroll regions; preserve real server sorting, pagination and keyboard stage selectors. |
| Forms | Existing native dialogs and dirty guards work; document dialogs vary. | Shared ERP modal/form primitives retaining existing interfaces and dirty guards. |
| Security | Session cookies, CSRF header, company membership checks and server write permissions already exist. | Preserve them; exercise session expiry, CSRF, member restrictions and company isolation. |
| Access | Session exposes company roles, not app entitlements. All active members can read implemented modules. | Match that contract. Do not invent an authorized-app API or hide valid member features. |
| Notifications | No notification/read/unread endpoint exists; dashboard exposes real recent activity. | On-demand company activity center, labeled as activity with no fabricated unread counter. |
| Maintainability | No TypeScript, Tailwind, ESLint, Vitest or Playwright configuration exists. | Incrementally type new primitives, enable Tailwind without resetting existing styles, add repeatable checks. |

API evidence: `accounts.views.session_data`, `companies.access.membership_for`,
`business.services.write_access`, `business.views.dashboard`, and
`frontend/src/services/api.js`. The backend uses Django JSON views, not DRF; this
interface task does not replace that working contract.

Validation results and remaining limits are recorded in
`../testing/UI-VERIFICATION.md` after executing the checks.
