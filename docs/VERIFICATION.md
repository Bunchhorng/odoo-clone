# Verification record

The [foundation follow-up](FOUNDATION.md) resolves the five findings in the original
[repository audit](REPOSITORY-AUDIT.md). The subsequent
[Contacts/Products phase](CONTACTS-PRODUCTS.md) adds the shared Vue components and
catalog workflows. This record describes current verification; the original audit's
55-test/14-group and foundation's 78-test/16-group figures remain historical snapshots.

Verified on **2026-10-28**, Asia/Bangkok, against the local Docker/MySQL stack.

## Automated checks

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
node scripts/verify-browser.mjs
```

- Django system check: passed, no issues.
- Migration consistency: passed, no uncommitted model changes.
- Backend suite: **101 tests passed** on an isolated MySQL test database.
- Vue production compilation: passed.
- Browser suite: **22 workflow groups passed**, no uncaught JavaScript errors or
  Vue runtime warnings. The focused catalog subset also passes separately.
- The additive catalog migration passed on the existing application database and
  the freshly created test database. The foundation milestone separately verified
  startup with fresh Compose volumes, test database privileges and proxy health.
- Git whitespace check: passed. `.env` remains untracked.

Backend coverage includes session/CSRF, role enforcement, company and related-ID
isolation, input validation, decimal rounding/snapshots, workflow transitions,
stock adjustments, purchase receipts/sales deliveries, duplicate fulfillment,
partial/full payments, payment retry IDs, demo idempotence, and company preferences.
It also verifies shared authentication throttles, single-use/expired reset tokens,
queued recovery mail/retries, password validation, session revocation, numeric ID
errors, pagination clamping, inactive relationships and duplicate payment activities.
Catalog coverage adds scoped role/type/category/stock filters, allowlisted stable
sorting, optional unique barcodes, category retention, bulk operations, CSV quoting,
size/header/row validation, duplicate warnings/errors, preview binding/expiry,
all-or-nothing import, and sequential/concurrent retry receipts.

Concurrent MySQL tests verify that two simultaneous deliveries cannot oversell,
two payments cannot exceed the remaining balance, a retried payment is recorded
once, and two owner demotions cannot remove the final owner.
Concurrent CSV confirmation records one batch, one receipt and one set of activity.

## Browser workflows

The Windows/Edge smoke test creates temporary ordinary accounts and isolated
companies, then removes only its own records in dependency order. It checks:

1. Protected route redirects, invalid credentials, login, session restoration/logout.
2. Company creation, ownership, company switching and persistence.
3. Team additions, active status changes, last-owner protection, member restrictions.
4. App launcher search and navigation to ten implemented applications.
5. Contact, product, opportunity, project, and task forms.
6. Opportunity/task stage changes persisted through the API.
7. Opening stock → quotation → confirmation → delivery → invoice → partial/full payment.
8. RFQ → purchase confirmation → receipt → vendor bill.
9. Print action invocation, live dashboard amounts, and payment history.
10. Mobile layouts at 375px, health failure/recovery, company data clearing, session expiry.
11. Contact role filters, phone search, table sorting and confirmed bulk archive/restore.
12. File input, CSV cell/error previews, quoted multiline import, and UTF-8 export/template blobs.
13. Product categories, leading-zero barcodes, category/type/stock filters and inactive retention.
14. Dirty dialog cancellation, clean Escape closure, Tab/Shift+Tab wrapping and mobile forms.
15. Read-only Contact/Product forms and hidden write/import/selection controls for members.
16. Account password change/recovery, token URL cleanup, single use and recovered sign-in.

The suite validates browser print invocation; it does not certify a saved PDF,
legal invoice layout, accounting compliance, or external payment execution.
No external payment is performed.

Generated screenshots and results are in ignored `.local/`, including
`erp-apps-desktop.png`, `erp-crm-desktop.png`, `erp-invoice-desktop.png`,
`erp-dashboard-desktop.png`, `erp-dashboard-mobile.png`, and
`auth-browser-results.json`. The catalog phase adds `catalog-products-desktop.png`,
`catalog-product-form-mobile.png` and `catalog-contacts-mobile.png`. Regenerate them
with the command above. The focused `--catalog-only` option writes
`catalog-browser-results.json` and does not replace the full-suite record.

## Local review

The stack is running with Vue on port **5173** and Django on **8001** in this
workspace's existing `.env`. Fresh clones use the example ports unless changed.
Sign in at <http://localhost:5173/login> and select **KERP Demo** to explore the
separate sample company. Existing company records and account passwords were preserved.

This verifies the implemented core. Full Odoo parity is not claimed; see
[ODOO-COVERAGE.md](ODOO-COVERAGE.md) for the remaining work.
