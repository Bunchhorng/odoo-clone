# Interface review workflow

Keep business/API changes separate from interface work when possible. The
30 October 2026 UI work preserves the in-progress business changes already in the
checkout and makes no backend contract changes.

Review the implementation in these groups (no commits were created automatically):

1. **Audit and foundations:** `docs/ui-ux/AUDIT.md`, semantic tokens, existing CSS
   consolidation, TypeScript/Tailwind and verification tooling.
2. **Shell and launcher:** shared header, app registry adapter, centralized module
   navigation, company selection, search, account/appearance and activity center.
3. **ERP views:** reusable List/Form/Kanban/Table/Modal components, compatibility
   adapters and existing catalog/document integrations.
4. **Verification and handoff:** component/API/contrast tests, real-backend browser
   checks and documentation.

Run `npm ci` in `frontend`, then `npm run check`. With Compose running, run
`npm run test:e2e` from `frontend` and `node scripts/verify-browser.mjs` from the
repository root. Run the existing Django suite through Compose. Browser checks
create randomly named test accounts/companies and remove only their own records.
Do not run two copies of the existing CDP script against its shared browser profile.

For every UI review, verify loading/error/empty/read-only states, light/dark theme,
keyboard navigation, narrow widths and unsaved changes. Never replace an API-backed
action with a visual-only success state. Never equate API health with business
module readiness. Check the actual company role before exposing write controls;
server authorization remains the authority.

Add future app availability and module menus in `src/data/apps.ts`, reuse existing
icons, and use semantic tokens instead of new global color overrides. Describe
whether grouping/filtering applies to the page or all server results. A true
notification inbox requires a backend unread/read contract before adding counters
or dismiss actions.

See [design/component contracts](../ui-ux/DESIGN-SYSTEM.md) and
[verification results](../testing/UI-VERIFICATION.md). The next milestone should
extend these primitives into the remaining specialized document/service screens,
add typed API response models and include Firefox/WebKit plus manual assistive
technology/browser-zoom checks.
