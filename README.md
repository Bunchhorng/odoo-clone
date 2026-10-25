# KERP

A Docker-based Django, Vue, and MySQL starter for a shared ERP workspace.

## Run locally

Install and start Docker Desktop. No host Python, Node, or MySQL installation is required.

1. Copy `.env.example` to `.env` (PowerShell: `Copy-Item .env.example .env`).
2. Replace the three `REPLACE_WITH_...` values with independent random secrets.
3. Run `docker compose up -d --build`.
4. Run `docker compose ps` and wait for all three services to be healthy.

The default launcher is <http://localhost:5173>. The backend is <http://localhost:8000>,
with administration at `/admin/` and the database-backed health endpoint at
`/api/v1/health/`. The same health endpoint works through port 5173's API proxy.

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

## Create an administrator

```sh
docker compose exec backend python manage.py createsuperuser
```

Use an email address rather than a username. For unattended local setup, fill in
the optional `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` in `.env`,
then run `docker compose exec backend python manage.py createsuperuser --noinput`.
Run this once; server startup never creates or resets users. After changing
environment variables, recreate the backend with `docker compose up -d backend`.

Sign in at `/admin/`, add a Company, then add Company Memberships for its users.
Membership roles are stored for future features; this starter does not expose
tenant-facing application APIs or implement membership-based permissions.

## Development

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
backend/         Django project; accounts, companies, and core apps
frontend/        Vue 3, Pinia, Vue Router, and Vite
infrastructure/  MySQL first-run test database permissions
docs/            Team workflow, roadmap, and design notes
compose.yml      Local development services and health checks
.env.example     Shareable configuration; .env stays ignored
```

This is a development setup: local ports bind to `127.0.0.1`, Django uses its
development server, and local settings default to `DEBUG=1`. Before production,
add production settings, a WSGI/ASGI server and reverse proxy, HTTPS, secret
management, and backup/storage operations as described in SETUP.md.
