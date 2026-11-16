# KERP UI verification — 30 October 2026

## Environment and commands

Windows, Node 24, headless Microsoft Edge, and the running Compose stack with
Django 5.2/MySQL 8.4. Frontend: `http://localhost:5175`; API traffic uses the existing
same-origin Vite proxy. Test records use random identifiers and are cleaned up.

```powershell
cd frontend
npm ci
npm run check
npm run test:e2e
cd ..
node scripts/verify-browser.mjs
docker compose exec -T backend python manage.py test --noinput
```

`npm run check` runs Vue type checking, ESLint, Vitest and the Vite production
build in sequence. The Compose check script and existing CI quality gate now use
this command. Browser checks run separately and need running services and Docker
CLI access. Playwright uses installed Edge locally, or Chromium in CI; install the
chosen browser before running in a fresh environment.

## Executed checks

| Check | Result |
| --- | --- |
| `npm run typecheck` / `vue-tsc --noEmit` | Passed; new TypeScript components plus the mixed JS/Vue project |
| `npm run lint` / `eslint . --max-warnings=0` | Passed |
| `npm run test` | 44 tests passed in 3 files |
| `npm run build` | Passed; production assets generated |
| `python manage.py test --noinput` in backend container | 177 tests passed using MySQL; test database created and destroyed |
| Dependency audit during final install | Zero known vulnerabilities reported after replacing the initial vulnerable Vitest version |
| Playwright | 17 tests passed; 0 skipped, 0 flaky; Edge, 3.8 minutes |
| Existing CDP business workflow suite | Passed all 51 workflow groups; no uncaught JS errors or Vue warnings; cleanup passed |

Vitest verifies role/company-aware app visibility, disabled unfinished apps,
trimmed search and clear/empty/loading/error/retry states, canceled/failed company
selection, keyboard disclosures, real table event contracts and page selection,
read-only status display, and stale-data suppression. API tests verify same-origin
cookies, CSRF headers, 401 session events without unsafe replay, 403 errors, and
rejection of successful non-JSON responses. Token tests verify AA normal-text
pairs and focus/control boundaries in both themes.

## Browser coverage and evidence

The Playwright suite uses real session login, company creation, contact creation,
opportunity data, company selection and the activity endpoint. Failure scenarios
intercept requests only inside the tests; no production component uses fake data.

- Five widths: 1440, 1024, 768, 390 and 320 CSS pixels, in light and dark themes.
- Launcher, contacts, CRM, sales, inventory, accounting, timesheets, helpdesk and
  team layout checks at each width. All 21 existing page routes also receive a
  no-error smoke check.
- Launcher search, keyboard focus, app switcher/module links, company session
  persistence, actual activity, native modal focus trapping/return and dirty guards.
- Contact grouping is explicitly limited to the current page.
- Axe WCAG A/AA scans: launcher, contact list/form, CRM board, dashboard and team
  in light/dark themes. These scans do not constitute a full accessibility audit.
- Module API failure versus healthy infrastructure, failed health probe and retry,
  member read-only controls, server-side write rejection, CSRF rejection and
  cross-company isolation.

The final Playwright run started at 22:06:55 Bangkok time and completed with all
17 tests passing. The preceding failed attempts exposed the navigation/mobile
issues and test-readiness problems described below; they are not counted as passes.

The final full CDP run completed at 22:17:35 Bangkok time in 140.7 seconds. It
verified real sales/delivery/invoice/payment flows, purchase/receipt/return flows,
stock corrections, accounting postings/reports/locks, service operations, catalog
imports/exports, password recovery, member permissions and expired-session
redirects. All 51 groups completed and test-owned records were cleaned up.

Playwright saves JSON results, screenshots and failure traces under ignored
`frontend/test-results/`. Existing workflow screenshots and JSON results are under
ignored `.local/`. The CDP helpers now wait for the mounted route, enabled controls
and asynchronously loaded select options; their navigation/status/sign-out
selectors follow the shared shell. The expiry check uses client-side navigation
to exercise the actual business API 401 handler.

Browser findings fixed during this work: duplicate ArrowDown handling when opening
an app disclosure, a 390px Helpdesk filter-label overflow, transient public shell
during initial session resolution, and payment history escaping its scroll region.

## Limits and manual checks

The 200% zoom check uses a 720×450 CSS viewport, the reflow equivalent of a
1440×900 desktop at 200%. Actual browser-toolbar zoom and OS scaling still need a
manual pass. No claim is made that a toolbar-zoom test was executed.

Firefox/WebKit, manual screen-reader behavior, high-contrast/forced-color mode,
and a complete keyboard pass through every specialized business action remain
follow-up work. The browser suite does not claim full Odoo module parity.

## Remaining API/product boundaries

The backend exposes company membership roles, not per-app entitlements. The
activity center uses the latest 12 events from the existing dashboard response;
there is no unread/read/dismiss notification contract. Shared chatter is read-only;
the existing Helpdesk note workflow keeps its real note API. Grouping does not
aggregate the entire paginated dataset. Legacy domain views are still JavaScript;
full response-model typing is a separate milestone.
