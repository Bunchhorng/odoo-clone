# Repository audit and Odoo readiness

**Foundation follow-up:** A-01 through A-05 are now resolved and regression-tested.
See [FOUNDATION.md](FOUNDATION.md) for the implementation and
[VERIFICATION.md](VERIFICATION.md) for current test results. The subsequent
[Contacts/Products phase](CONTACTS-PRODUCTS.md) extends the catalog and Vue components.
The diagnosis and baseline results below preserve
the original audit snapshot; they do not describe the current open-defect count.

Audit date: **2026-10-28, Asia/Bangkok**. Scope: the current repository working tree,
its local Docker/MySQL runtime, documentation, baseline checks, and targeted probes.
Application source was reviewed without making application fixes. Existing modified
and untracked feature work was preserved.

**Assessment:** KERP is a functional ERP prototype with connected commercial
workflows. The normal test suite passes, but targeted checks reproduced **five
defects**, including a financial-document confirmation mismatch. Broad Odoo parity
and production readiness remain incomplete. The companion
[74-capability parity matrix](ODOO-PARITY-MATRIX.md) provides evidence, boundaries,
priorities, and acceptance conditions; its [CSV copy](ODOO-PARITY-MATRIX.csv) is
available for spreadsheet planning.

## Findings

All five findings were **open at the original audit** and are now resolved by the
foundation follow-up. P1/high means fix before
relying on the affected transactional workflow; P2/medium means a concrete defect
with a narrower impact or workaround. These severities are separate from the
matrix's development priorities.

| Finding | Severity | Confirmed impact | Reproduction |
| --- | --- | --- | --- |
| A-01 | P1 / High | Confirm/Issue discards unsaved form changes and transitions older server values | Browser: order and invoice |
| A-02 | P2 / Medium | Company switch can show an empty list despite existing records, with no pager to recover | Browser: Contacts on page two |
| A-03 | P2 / Medium | Retrying one payment creates duplicate completion activities | Isolated MySQL API probe |
| A-04 | P2 / Medium | Malformed numeric record IDs return HTTP 500 instead of JSON 400 | Isolated MySQL API probe, two inputs |
| A-05 | P2 / Medium | Unchanged inactive relationships prevent ordinary form edits | Browser and isolated MySQL API probe |

### A-01 — Dirty documents can be confirmed or issued using older values

Evidence: [OrdersView.vue:58](../frontend/src/views/OrdersView.vue#L58),
[OrdersView.vue:29](../frontend/src/views/OrdersView.vue#L29),
[InvoicesView.vue:25](../frontend/src/views/InvoicesView.vue#L25).

The Save path submits the form, but the Confirm/Issue path submits only an action.
No dirty-form check, save-before-action step, or transition guard connects them.
After the action, refresh replaces the displayed edits with server values, and the
document is no longer editable in its new state.

Reproduced in the browser:

1. Save a quotation with quantity **2**, unit price **25.00**, and **7%** tax:
   saved total **53.50**.
2. Change the visible quantity to **3** and unit price to **30.00**. The preview
   displays **96.30**.
3. Select **Confirm sale** without selecting Save.
4. The confirmed document contains **2 × 25.00**, total **53.50**. The visible
   edits were discarded.

The same separation affects invoice issue: editing the date to **2026-10-27** and
due date to **2026-11-30**, then selecting Issue, produced an issued invoice dated
**2026-10-28** with **no due date**.

Recommended fix: consistently block transitions while a form is dirty and require
Save/Discard, or explicitly validate and save the form before transitioning. Add a
route-leave guard for unsaved edits. If concurrent editors are supported, add a
version/updated-at precondition so confirmation cannot silently target a stale
version.

Acceptance: edit quantity, price, party/date, due date, and notes on existing drafts;
every Confirm/Issue must either persist the displayed valid values or visibly block
the transition. Test sales, purchases, customer invoices, and vendor bills. Invalid
unsaved fields must never be bypassed by a transition.

### A-02 — Pagination survives a company switch and strands valid records

Evidence: [CatalogView.vue:18](../frontend/src/views/CatalogView.vue#L18),
[CatalogView.vue:38](../frontend/src/views/CatalogView.vue#L38),
[CatalogView.vue:135](../frontend/src/views/CatalogView.vue#L135).

The list page is preserved when the company changes. Data reloads for that old page,
but pagination controls are shown only when the new company's total exceeds its
page size. A small company can therefore have records but render an empty page with
no Previous button.

Browser reproduction:

1. Company A has **25** contacts, with a card page size of **24**.
2. Go to page two, then select Company B, which has **one** contact.
3. The header reports **1 record**, there are **0 cards**, the screen says **No
   contacts yet**, and **no pagination control** is rendered.

This is a visibility defect, not a cross-company data leak. The same retained-page
pattern appears in [OrdersView.vue:17](../frontend/src/views/OrdersView.vue#L17) and
[InvoicesView.vue:13](../frontend/src/views/InvoicesView.vue#L13); runtime reproduction
in this audit was performed on Contacts.

Recommended fix: reset list page state before fetching on company changes, and
reset/clamp it after search/filter changes that reduce the result count. Share that
behavior across catalog, order, invoice, and stock list components.

Acceptance: switch from a later page in a large company to a company with one
record; the one record must appear on page one. Repeat for filtered lists and for
a company with no records. Preserve stale-response protection.

### A-03 — A payment retry emits another payment-completion activity

Evidence: [services.py:226](../backend/apps/business/services.py#L226) and
[views.py:227](../backend/apps/business/views.py#L227).

The payment service correctly returns an existing Payment when its request UUID
is retried. The view then unconditionally emits a new `Payment ...` activity even
when no new financial event occurred.

An isolated API probe submitted the same partial-payment body and request UUID
twice. Both calls returned 200; the database contained **one Payment** and **two
payment activities**. The payment amount and remaining balance were correct.
The visible event feed can nevertheless imply two receipts.

Recommended fix: propagate whether a payment was newly created and emit the
completion activity only once, within the same transaction. Define separate
attempt/retry logging if required. Consider unique event keys for other idempotent
document actions too.

Acceptance: sequential and concurrent retries produce one Payment and one
completion activity. Reusing the UUID with different details must still return 409.

### A-04 — Invalid numeric identifiers can escape validation as HTTP 500

Evidence: [services.py:43](../backend/apps/business/services.py#L43) and
[core/api.py:28](../backend/apps/core/api.py#L28).

`positive_id` accepts strings according to `str.isdigit()` and then calls `int()`
without handling conversion errors. Some Unicode digit characters are not accepted
by `int`, and excessively long digit strings exceed Python's integer-conversion
limit before the intended range check runs.

Both inputs below produced HTTP **500** from `POST .../erp/stock/` as an
authenticated writer:

```json
{"product_id":"\u00b2","quantity":"1","reason":"Audit"}
```

The second input uses a string containing **5000 copies of `9`** for product_id.
The expected contract is a JSON **400** validation error. This audit does not
claim an unauthenticated authorization bypass; the affected probe used owner access.

Recommended fix: validate a bounded ASCII decimal representation before conversion,
handle conversion exceptions, then check the database ID range. Keep unexpected
programming errors distinguishable from client input errors.

Acceptance: valid IDs work; superscripts, oversized IDs, booleans, arrays, negative
IDs, and nonnumeric strings return documented 4xx JSON responses, never an input-
triggered 500. Verify all shared related-ID call sites.

### A-05 — Forms resend unchanged inactive relationships and fail unrelated edits

Evidence: [CatalogView.vue:45](../frontend/src/views/CatalogView.vue#L45),
[CatalogView.vue:55](../frontend/src/views/CatalogView.vue#L55),
[CatalogView.vue:64](../frontend/src/views/CatalogView.vue#L64), and
[catalog.py:61](../backend/apps/business/catalog.py#L61).

The form loads only active relation choices, but its payload resubmits every field,
including an unchanged relationship to a now-inactive teammate. The backend rejects
that relationship as if it were a new assignment.

Reproduction: assign an existing task to a teammate, disable that teammate's company
membership, open the task, change **only its title**, and select Save. The UI returns
**Choose an active teammate in this company.** A title-only PATCH for the same task
returns **200**, while the form-equivalent full payload returns **400**. The actual
browser form reproduced this failure.

Recommended fix: send only changed fields and preserve/display historical inactive
choices clearly. A newly selected assignee must still be active. Apply the same
relationship policy consistently to archived customers/products/projects; those
other forms were identified by source review rather than all reproduced in-browser.

Acceptance: title/notes/stage edits remain possible after the existing assignee's
access is disabled, without silently reactivating or replacing the person. New
assignments to inactive or foreign-company users must remain rejected.

## Verification performed

| Check | Audit result | Scope/limit |
| --- | --- | --- |
| Django system checks | Passed | Current local settings |
| Migration consistency | Passed | No missing model migrations |
| Existing backend suite | **55 passed** | Includes MySQL concurrent stock/payment/ownership tests |
| Vue production build | Passed | Compilation only; does not deploy production hosting |
| Browser workflow coverage | **14 workflow groups passed** | Current smoke harness; targeted cases were also exercised in an audit copy |
| Targeted API probes | Three observation probes completed | Reproduced A-03, A-04, and A-05; these intentionally observe current defects rather than certify correctness |
| Targeted UI probes | Four counterexamples recorded | A-01 order/invoice, A-02 company pagination, A-05 inactive relation |
| npm advisory check | **0 reported vulnerabilities** | Installed frontend tree, including development dependencies, at audit time |
| Python dependency consistency | Passed | `pip check`; no Python advisory/CVE scan was performed |
| Deployment check | **5 warnings** | HSTS, HTTPS redirect, secure session cookie, secure CSRF cookie, DEBUG |
| Whitespace/config checks | Passed | `git diff --check`, `docker compose config --quiet` |

The targeted probes explain why a green baseline does not establish business
correctness or parity. They should become expected-correctness regression tests
when the fixes are implemented.

Commands used for the baseline:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
node scripts/verify-browser.mjs
docker compose exec -T frontend npm audit --json
docker compose exec -T backend python -m pip check
docker compose exec -T backend python manage.py check --deploy
docker compose config --quiet
git diff --check
```

Audit helpers and raw UI observations were written to ignored `.local/`:
`audit_probes.py`, `prepare_audit_browser.py`, `audit-browser.mjs`,
`audit-browser-flow.mjs`, and `audit-ui-results.json`. API probes used the isolated
MySQL test database and dropped it afterward. Browser probes created temporary
accounts/companies and removed their records in dependency order. The existing
demo/company records, passwords, configuration, and dependencies were preserved.
These local helpers are not part of a clean clone; the reproduction steps above
are the portable record. No exploit traffic was sent to Odoo.

## Architecture and positive evidence

The application has three local services: Django, Vue/Vite, and MySQL. Account,
company, core, and business apps are installed. Business logic is primarily in
`business/services.py`; catalog allowlists/validation are in `catalog.py`; APIs are
plain Django views using the shared JSON/auth wrapper. Vue uses Pinia, Vue Router,
and company-scoped request/loading helpers.

- Active membership and active-company checks are enforced in the API, with no
  automatic superuser bypass for business endpoints.
- CSRF/session behavior, cross-company IDs, role restrictions, and revoked access
  have existing tests. The reviewed Vue paths use escaped template output.
- Decimal arithmetic calculates document totals on the server, including explicit
  line rounding. Confirmed documents reject normal API edits.
- Company-row locking protects numbering and transactional stock/payment rules.
  MySQL concurrency tests exercise overselling, overpayment, repeated payment UUIDs,
  and final-owner changes.
- Financial payment idempotency itself works; A-03 concerns its activity side effect.
- Business administration is read-only, and protected references discourage deleting
  transaction history. Membership/user administration remains a trusted global path.
- `.env` is ignored and untracked. Local host ports bind to 127.0.0.1.

## Known product boundaries and parity gaps

These are explicit capability limits, distinct from the five defects above:

- One invoice/bill per order via a one-to-one relationship. Cancelling that invoice
  does not provide a replacement/reissue route. No credit notes or refunds exist.
- Full-order delivery/receipt only; there are no reserved, delivered, returned, or
  invoiced quantities per line. Stock has one pool per company and no valuation.
- Invoicing records manual balances; there are no accounts, journals, double-entry
  posting, bank reconciliation, or statutory accounting statements.
- Taxes are manual percentages. Currency is one of seven fixed two-decimal choices
  per company, locked after the first order; there is no FX engine.
- CRM opportunities are not linked to quotations. Task/opportunity stages are fixed.
- All active members can read company business data; owner/admin roles grant broad
  write access. There are no app-level finance, stock, sales, or own-document roles.
- Dashboards cover all dates; activity is the latest twelve summary events, without
  field diffs or complete audit-history navigation.
- PDF support is a browser print invocation. The smoke test stubs printing and does
  not validate PDF bytes, pagination, or a jurisdiction-specific invoice layout.
- HR/payroll, manufacturing, POS, website/eCommerce, subscriptions, and several other
  Odoo app families have no implementation in the inspected models/routes.

The [parity matrix](ODOO-PARITY-MATRIX.md) uses Odoo 19 documentation as a fixed
comparison baseline, with edition-dependent scope left explicit. At the original audit it contained
**16 Implemented**, **16 Partial**, **36 Missing**, and **6 Defect** rows. The
foundation follow-up now has **23 Implemented**, **18 Partial**, **33 Missing**,
and **0 Defect** rows in the same selected checklist.
Counts refer to this selected checklist and must not be presented as an Odoo parity
percentage. See the official [Odoo 19 application docs](https://www.odoo.com/documentation/19.0/applications.html)
and [edition comparison](https://www.odoo.com/page/editions) for the reference scope.

## Repository state and maintainability

- HEAD is **7040f04 — Initialize KERP Docker development starter**. The audit included
  the substantial modified and untracked implementation beyond that commit. A clone
  of HEAD alone does not reproduce this working application. No commit, reset, or
  cleanup of the user's feature work was performed.
- No `.github` CI workflow or equivalent CI configuration was found in the inspected
  file inventory. Checks are currently manual scripts. No explicit frontend lint,
  type-check, or unit-test script is present in package.json.
- Business modules share one `business` app and broad company roles. This is simple
  for the current scope but will need explicit domain boundaries/permissions as
  finance, HR, manufacturing, and other apps grow.
- Several Vue templates are very long single lines, and shared record handling
  combines resource configuration, options, forms, pagination and board logic.
  Improve formatting and extract focused components while preserving behavior.
- Company-wide write locks are correctness-friendly but serialize unrelated writes.
  No load test or measured capacity target was established. Dashboard balance and
  low-stock calculations also iterate company data in Python; profile realistic
  volumes before making scale claims.
- UI form options fetch all active records in batches of 100. There is no relation
  autocomplete/virtualization. Large contact/product sets need measured usability
  and performance work.
- Official-source comparison was documentation-based. No licensed Enterprise instance,
  production deployment, saved-PDF validation, accessibility certification, backup
  restore drill, container image scan, or executable Odoo differential test was run.

## Production release gates

The current setup is intentionally local development, as the setup guide states.
The deployment-check warnings are expected for that setup and are not reported as
surprise exploitable production vulnerabilities. Before public deployment:

1. Resolve A-01 and add regression coverage for all findings.
2. Commit/review a reproducible release, then test install/migrations from a clean
   checkout using fresh isolated infrastructure.
3. Add production settings, application/static hosting, HTTPS and secure-cookie
   configuration; disable DEBUG and resolve deployment-check warnings.
4. Add login throttling, account recovery, and an explicit per-app access policy.
5. Establish backup/restore, monitoring, dependency advisory checks, and CI gates.
6. If used for real finance, first define the required accounting, tax, document,
   reversal and audit rules. Current invoice balances alone do not meet that scope.

## Recommended next work

| Sequence | Work item | Done when |
| --- | --- | --- |
| 1 | Fix A-01 to A-05 | New regressions reproduce the old defects and pass after fixes; baseline checks remain green |
| 2 | CRM-to-quotation and app-specific permissions | Linked documents and role-specific read/write examples pass |
| 3 | Partial stock/invoice model and recovery workflows | Partial receipt/delivery/invoice, return, cancellation replacement and credit examples reconcile |
| 4 | Accounting foundations and chosen localization | Journal posting balances and agreed accounting/document examples pass |
| 5 | Import/export, deeper reporting, production controls | Data round-trips, clean-clone CI, restore drills and deployment gates pass |
| 6 | Additional Odoo app families | Each selected app has agreed fields, transitions, roles and end-to-end acceptance tests |

This original audit delivered the findings and plan. Remediation of its five
defects is now complete; broader parity and production work remains tracked in
[the current matrix](ODOO-PARITY-MATRIX.md).
