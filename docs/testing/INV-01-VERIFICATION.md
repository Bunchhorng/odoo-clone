# INV-01 verification — 30 October 2026, Asia/Bangkok

Scope and API rules: [INVENTORY-V2-INV-01.md](../INVENTORY-V2-INV-01.md).
Branch: `feature/inventory-warehouse-locations`.

## Executed checks

| Check | Result |
| --- | --- |
| `docker compose exec -T backend python manage.py check` | Passed; no system-check issues |
| `docker compose exec -T backend python manage.py makemigrations --check --dry-run` | Passed; no changes detected |
| `docker compose exec -T backend python manage.py migrate --noinput` | Applied business 0007, 0008 and 0009 successfully |
| `docker compose exec -T backend python manage.py test --noinput` | 192 tests passed, including all 177 previous tests and 15 INV-01 tests; disposable MySQL test database |
| `npm run check` in frontend | Type checking, ESLint, 46 Vitest tests and production build passed |
| `docker compose exec -T frontend npm run build` | Passed; production assets generated in the frontend container |
| `npm run test:e2e` in frontend | 18 Playwright tests passed; no skipped/flaky cases |
| `node scripts/verify-browser.mjs` | All 51 business workflow groups passed; no Vue warnings/uncaught JS errors; cleanup passed |
| Parity Markdown/CSV verifier | Passed: 74 rows, 25 Implemented / 28 Partial / 21 Missing / 0 Defect; all 7 verifier regression tests passed |

The final full browser regressions completed at 23:18 Bangkok time. Both suites
created isolated temporary users/companies and removed their own fixtures.
Protected inventory references required updating test cleanup order: movements,
warehouses, leaf locations, then test companies. No existing user data is selected
by those cleanup routines.

## Acceptance evidence

- Warehouse creation creates or selects a real internal root. Codes normalize and
  are unique per company. Additional warehouses edit/archive/restore without
  deletion. Failed creation rolls back any automatically created location.
- Default posting records remain active; root identity, protected location types
  and histories cannot be reassigned. Referenced locations are protected by FKs.
- Location types, compatible parents, cycles, active ancestors and full-subtree
  depth are validated. Company-scoped filters/pagination reject malformed and
  foreign IDs. Members can read but cannot create, update or archive.
- Existing adjustment/reversal APIs retain IDs and signed balances. Existing
  receipt/return/delivery/invoice/report calls retain document/line/receipt links.
  The original business/API/concurrency suites and real browser workflows remain
  green.
- A real `MigrationExecutor` upgrade from 0006 to 0009 preserves **every original
  movement field**, row count and total, assigns receipt/delivery/return/reversal
  endpoints, retains zero/unusual-sign legacy rows, and permits idempotent backfill.
- Failed correction backfill rolls back all default/configuration rows and partial
  endpoint assignments; correcting only the disposable test fixture allows retry.
  Foreign-company legacy references fail before any assignments.
- Bulk movement inserts without endpoints fail the non-null constraint. Model/API
  validation rejects cross-company endpoint references.
- Playwright exercises both new forms, warehouse archive/restore, parent choices,
  hierarchy display, 320px layout, navigation and owner/member permissions. The
  suite also smoke-checks all existing routes plus the two new inventory routes.

## Existing local-data fingerprint

Before migration, the local database contained 8 movements and 3 invoices.
Before/after SHA-256 fingerprints match for all original movement fields and all
invoice/journal records. The backfill created 3 default warehouses and 12 company
locations; all 8 movements received endpoints, with zero missing endpoints.
No movement was duplicated, replaced, renumbered or re-quantified. Migration
logging reported no zero/unusual-sign originals in this particular database;
the upgrade tests cover both cases explicitly.

Ignored evidence files: `.local/inv01-before.txt`, `.local/inv01-after.txt`,
`.local/auth-browser-results.json`, and `frontend/test-results/ui-results.json`.
Playwright includes an inventory hierarchy mobile screenshot under its test
output directory. Tests first caught an incorrect invoice-response expectation in
the new acceptance case; that expectation was corrected to the existing contract,
and the final full suite passed.

## Limits / blockers

No remaining INV-01 acceptance blocker. Historical physical allocation remains
inferred because the old ledger had no warehouse/bin information. Default-only
posting, archive protections and configuration-only additional warehouses are
intentional scope boundaries. No transfers, reservations or partial sales delivery
work was started. Manual assistive-technology/browser-toolbar zoom and additional
browser engines remain outside this inventory milestone's verification.
