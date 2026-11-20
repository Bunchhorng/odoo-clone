# KERP

A Django, Vue, and MySQL ERP project with an Odoo-style app launcher and connected
core workflows: contacts, CRM, sales, purchase, inventory, invoices/payments,
projects/tasks, reporting, and company/team access.

This is an independent implementation with a defined feature set, not full Odoo
parity. See the [coverage matrix](docs/ODOO-COVERAGE.md) for working features and
remaining applications, and the [ERP walkthrough](docs/ERP-GUIDE.md) to try it.

Start with [SETUP.md](SETUP.md) to run the code, then follow the
[user guide](docs/USER-GUIDE.md). Windows users can run
`powershell -ExecutionPolicy Bypass -File scripts/start.ps1` from the project root
to prepare local configuration and start Docker services. Existing `.env` secrets
are preserved.

The [Contacts and Products guide](docs/CONTACTS-PRODUCTS.md) covers categories,
barcodes, filtering/sorting, bulk archive/restore and validated CSV transfers.
Developers can follow [the Vue component guide](docs/VUE-COMPONENTS.md) to extend
the shared controls, tables and dialogs.

The [CRM and Sales guide](docs/CRM-SALES.md) covers linked quotations, concurrent
document edits, archived relationships and cancelled-invoice correction.
The [Purchase and Inventory guide](docs/PURCHASE-INVENTORY.md) covers partial
receipts, supplier returns awaiting replacement, stock tracing and count reversals.

## Run locally

Install and start Docker Desktop. No host Python, Node, or MySQL installation is required.

1. If `.env` is absent, copy `.env.example` to `.env` (PowerShell: `Copy-Item .env.example .env`). Keep an existing `.env`.
2. In a new configuration, replace the three `REPLACE_WITH_...` values with independent random secrets.
3. Run `docker compose up -d --build`.
4. Run `docker compose ps`: db/backend/frontend should be healthy and mailer running.

The default application is <http://localhost:5175>. The backend is <http://localhost:8000>,
with administration at `/admin/` and the database-backed health endpoint at
`/api/v1/health/`. The same health endpoint works through port 5175's API proxy.

If port 8000 is already occupied, set `BACKEND_PORT=8001` in `.env` and use
<http://localhost:8001/admin/> and <http://localhost:8001/api/v1/health/>.
`FRONTEND_PORT` similarly changes the frontend host port. If you change the
frontend port, update `DJANGO_CSRF_TRUSTED_ORIGINS` to match. Container-to-container
addresses stay `db:3306` and `backend:8000` regardless of host port overrides.
MySQL is available only on the internal Compose network.

## Verify

```sh
docker compose exec backend python manage.py check
docker compose exec backend python manage.py showmigrations
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py test
docker compose exec frontend npm run build
```

For the full Windows browser run and parity-record verification:

```sh
node scripts/verify-browser.mjs
python scripts/verify-parity.py
python -m unittest discover -s scripts -p test_verify_parity.py
```

Browser checks require host Node.js 22+ and Edge; parity checks use Python 3.9+.
See [E2E and parity verification](docs/E2E-PARITY.md) for results, evidence,
report artifacts and the remaining Odoo capability gaps.

## Create an administrator

```sh
docker compose exec backend python manage.py createsuperuser
```

Use an email address rather than a username. For unattended local setup, fill in
the optional `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` in `.env`,
then run `docker compose exec backend python manage.py createsuperuser --noinput`.
Run this once; server startup never creates or resets users. After changing
environment variables, recreate the backend with `docker compose up -d backend`.

Sign in at <http://localhost:5175/login>, create a company in **Companies**, and
open **Team** to add existing user accounts. You become the company's owner.
Company access is enforced by the API on every request. Staff and superusers also
need a company membership to use its application APIs.

Owners manage all roles. Administrators manage ordinary members. Members can view
the team. The application prevents removal of the final active owner. Team accounts
are managed in Django Admin; adding a teammate sends no email. Users can change
their password from the account link and request recovery from the sign-in screen.
See [the foundation guide](docs/FOUNDATION.md) for local recovery mail and limits.

## Development

To explore a separate sample company with your existing account:

```sh
docker compose exec backend python manage.py seed_demo --email admin@kerp.local
```

Replace the email if needed, reload KERP, and select **Odoo Demo**. This creates
sample data in its own company and leaves existing companies/passwords unchanged.
Repeating the command leaves the existing demo unchanged. Verify, preview, or
remove only that isolated workspace with `--verify`, `--dry-run`, or
`--reset-demo --confirm-reset`; see [Demo seeders](docs/DEMO-SEEDERS.md). The
command refuses non-development Django environments.

Source directories are mounted into the development containers. Django reloads
Python changes and Vite reloads Vue changes. When dependency files change, rebuild
with `docker compose up -d --build`. Frontend startup uses `npm ci` so its named
dependency volume matches the committed lockfile.

Only model changes need new migrations:

```sh
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
```

Commit migration files and `frontend/package-lock.json`. Coordinate migration
merge order across branches. See [SETUP.md](SETUP.md) and
[team workflow](docs/TEAM-WORKFLOW.md).

The MySQL init script grants the application user privileges on the exact
`test_<MYSQL_DATABASE>` database so Django tests can create and drop it.
It runs only on the first initialization of a new database volume. Changing
database credentials in `.env` does not change an existing MySQL account.
Do not delete a database volume to troubleshoot valuable data.

Stop the stack with `docker compose stop`, or remove containers and their network
with `docker compose down`. Both preserve the database volume.

## Structure

```text
backend/         Django session APIs, company access, admin, and automated tests
frontend/        Vue 3, Pinia, Vue Router, and Vite
infrastructure/  MySQL first-run test database permissions
docs/            Team workflow, roadmap, and design notes
scripts/         Windows startup and verification helpers
compose.yml      Local development services and health checks
.env.example     Shareable configuration; .env stays ignored
```

This is a development setup: local ports bind to `127.0.0.1`, Django uses its
development server, and local settings default to `DEBUG=1`. Before production,
add production settings, a WSGI/ASGI server and reverse proxy, HTTPS, secret
management, and backup/storage operations as described in SETUP.md.

## Deploy on Render, Cloudflare, and Neon

The repository includes a production `render.yaml`, PostgreSQL/Neon settings,
credentialed CORS for the Vue static site, and a password-reset mail worker.
Follow the [Render + Cloudflare + Neon deployment guide](docs/DEPLOYMENT_RENDER_CLOUDFLARE_NEON.md)
to configure the required secrets, domains, DNS, and release checks. Local Docker
development remains on MySQL; a MySQL database is not migrated to Neon automatically.

## Documentation

- [Project completion report](docs/PROJECT-STATUS-REPORT.md): delivered workflows, all 49 unfinished capability rows, production gaps, and completion priorities.
- [Setup and troubleshooting](SETUP.md): install, run, verify, and restart.
- [User guide](docs/USER-GUIDE.md): complete the first company/team workflow.
- [Developer guide](docs/DEVELOPMENT.md): architecture, files, and adding a module.
- [API reference](docs/API.md): requests, responses, and permissions.
- [Step-by-step roadmap](docs/ROADMAP.md): completed work and future modules.
- [ERP walkthrough](docs/ERP-GUIDE.md): from contact creation to a paid invoice.
- [Business API](docs/ERP-API.md): catalog, orders, stock, invoices, and projects.
- [Odoo coverage](docs/ODOO-COVERAGE.md): implemented scope and remaining gaps.
- [Verification record](docs/VERIFICATION.md): test results and browser workflows.
- [Repository audit](docs/REPOSITORY-AUDIT.md): reproduced defects, risks, and remediation priorities.
- [Odoo parity matrix](docs/ODOO-PARITY-MATRIX.md): 74 evidence-based capability rows; [CSV](docs/ODOO-PARITY-MATRIX.csv) for spreadsheets.
- [Docker + ERP Core + Authentication](docs/FOUNDATION.md): resolved audit findings, account recovery, throttling, Docker/CI verification.
- [Production deployment](docs/DEPLOYMENT_RENDER_CLOUDFLARE_NEON.md): Render Blueprint, Neon, Cloudflare DNS, and operational checks.

The [Accounting & integration guide](docs/ACCOUNTING-INTEGRATION.md) covers the new
ledger, posting-date locks, financial reports and source-document links. Open the
Accounting app; import historical postings if the incomplete-reports notice appears.

[Employees, Timesheets and Helpdesk](docs/SERVICE-APPLICATIONS.md) are available
from Apps. Link existing Team accounts in Employees to enable personal time logging.
