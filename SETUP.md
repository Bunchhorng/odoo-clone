# Run KERP step by step

Run all commands from the project root: the folder containing `compose.yml`.
Docker runs Django, Vue, and MySQL together. You do not need to install Python,
Node.js, or MySQL on your computer for the normal setup.

## 1. Install and start Docker

Install Docker Desktop. On Windows, enable its WSL2 engine. Start it and wait until
the engine is ready. On Linux, Docker Engine with the Compose plugin also works.

```powershell
docker --version
docker compose version
docker info
```

The last command must connect to the engine. If it fails, start Docker Desktop or
check your Docker permissions before proceeding.

## 2. Start the project

### Windows shortcut

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

This checks Docker, creates `.env` only if absent, fills three independent random
secrets on first creation, and builds/starts the services. It preserves an existing
`.env` and database. If an existing `.env` contains placeholders, edit those values
using the manual instructions below and rerun the script.

### Manual setup (all platforms)

If `.env` does not exist, copy the example:

```powershell
Copy-Item .env.example .env
```

On Linux/macOS, use `cp .env.example .env` instead. **Keep an existing `.env`; do not
overwrite it.** In your new `.env`, replace these values with independent random
secrets:

```text
DJANGO_SECRET_KEY=REPLACE_WITH_DJANGO_SECRET_KEY
MYSQL_PASSWORD=REPLACE_WITH_MYSQL_APP_PASSWORD
MYSQL_ROOT_PASSWORD=REPLACE_WITH_MYSQL_ROOT_PASSWORD
```

Do not reuse one password for all three values. Keep `.env` private and out of Git.
The backend's `MYSQL_HOST` is `db` inside Docker, not localhost.

```powershell
docker compose up -d --build --wait --wait-timeout 300
docker compose ps
```

The `db`, `backend`, and `frontend` services should be healthy; `mailer` should be
running. The first build
can take several minutes. MySQL starts first, then Django applies committed
migrations, then Vue starts. Startup never creates or resets user passwords.
The mailer processes recovery requests. See [FOUNDATION.md](docs/FOUNDATION.md) for
account recovery and local console-mail instructions.

## 3. Open the application

| Purpose | Default address |
| --- | --- |
| KERP sign-in | <http://localhost:5175/login> |
| In-app guide | <http://localhost:5175/setup> |
| Django administration | <http://localhost:8000/admin/> |
| API + database health | <http://localhost:8000/api/v1/health/> |
| Health through Vue's proxy | <http://localhost:5175/api/v1/health/> |

Use the ports from your `.env`. For example, `BACKEND_PORT=8001` makes the admin
address <http://localhost:8001/admin/>. The frontend stays on 5175 unless
`FRONTEND_PORT` changes. Use `localhost` consistently to avoid separate cookie jars.

## 4. Create the first administrator

```powershell
docker compose exec backend python manage.py createsuperuser
```

Enter an email and password interactively. Then sign in at the KERP frontend.
If the account already exists, sign in with it or reset its password:

```powershell
docker compose exec backend python manage.py changepassword you@example.com
```

Optional unattended setup: fill `DJANGO_SUPERUSER_EMAIL` and
`DJANGO_SUPERUSER_PASSWORD` in `.env`, recreate the backend with
`docker compose up -d backend`, then run
`docker compose exec backend python manage.py createsuperuser --noinput` once.
These variables are only for that explicit command.

## 5. Create a company and add your team

1. In KERP, open **Companies** and create your company. You become its owner.
2. In Django Admin, create ordinary user accounts for your teammates.
3. In KERP, open **Team** and add an existing account's email.
4. Choose **member**, **admin**, or **owner** according to the access required.
5. Teammates sign in with their account credentials and select the company.

No invitation email is sent. One account can belong to several companies with
different roles. Follow [the user guide](docs/USER-GUIDE.md) for the complete flow.

## 6. Verify the code

To explore sample business workflows first, create a separate demo company:

```powershell
docker compose exec backend python manage.py seed_demo --email admin@kerp.local
```

Use an existing account's email, reload the frontend, and select **KERP Demo**.
The command preserves existing companies/passwords and does not duplicate an
existing demo. Follow [ERP-GUIDE.md](docs/ERP-GUIDE.md) for the complete sales,
purchasing, inventory, invoicing, and project workflows.

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
```

Equivalent individual commands:

```powershell
docker compose exec backend python manage.py check
docker compose exec backend python manage.py showmigrations
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py test --noinput
docker compose exec frontend npm run build
```

Expected: no Django issues, no missing migrations, passing tests, and a successful
Vue build. The backend tests use a separate `test_<MYSQL_DATABASE>` database.

Optional Windows browser check, with Node.js 22+ and Microsoft Edge installed:

```powershell
node scripts/verify-browser.mjs
```

This uses temporary test accounts and companies, exercises real browser workflows,
cleans up its own database records, and writes screenshots/results to ignored
`.local/`. It does not require or change your administrator credentials.
It requires the local console email backend so it does not send real mail.

## 7. Edit and restart

Edit `backend/` or `frontend/src/`; Django and Vite reload the mounted source.
For dependency changes, rebuild:

```powershell
docker compose up -d --build
```

For model changes only:

```powershell
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
```

Commit migrations and `frontend/package-lock.json`. See
[DEVELOPMENT.md](docs/DEVELOPMENT.md) for the code map.

## 8. Stop and start later

```powershell
docker compose stop
docker compose up -d
```

`docker compose down` also preserves the database volume while removing containers
and their network. Do not add `-v` if you want to keep your database.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| Cannot connect to Docker | Start Docker Desktop and wait for the engine; check `docker info`. |
| Port 8000 is occupied | Set `BACKEND_PORT=8001` in `.env`, then run `docker compose up -d`. |
| Frontend port is occupied | Change `FRONTEND_PORT` and update `DJANGO_CSRF_TRUSTED_ORIGINS` to include that port for localhost and 127.0.0.1; recreate services. |
| Service stays unhealthy | Run `docker compose logs --tail=80 db backend frontend` and read the first error. |
| MySQL rejects credentials after changing `.env` | Existing volumes retain the original MySQL accounts. Restore matching secrets or update credentials deliberately. Do not delete valuable data to fix this. |
| Tests cannot create their database | The init script runs only when the MySQL volume is first initialized. A DBA can grant the application user privileges on the exact `test_<MYSQL_DATABASE>` database; see `infrastructure/mysql/initdb/01-test-database.sh`. |
| Sign-in fails | Use email rather than username. Check the account is active in Django Admin; reset the password if needed. |
| CSRF/security token error | Reload the page, use localhost consistently, and check trusted origins if you changed ports. |
| Team account cannot be added | Create its active user account in Django Admin first. For an existing membership, reactivate its row instead of adding a duplicate. |
| No companies after sign-in | Create one, or ask an owner to add your email. Reload after another person changes your access. |
| Cannot remove an owner | Promote another active account to owner first. One active owner must remain. |

## Scope and deployment

The app includes company access and core contacts, CRM, product, sales, purchasing,
inventory, invoice/payment, project/task, and dashboard workflows. Advanced module
features and additional applications remain; see [ODOO-COVERAGE.md](docs/ODOO-COVERAGE.md)
and [ROADMAP.md](docs/ROADMAP.md). This is not full Odoo feature parity.

This stack is for local development: ports bind to 127.0.0.1, Django uses its
development server, Vite serves Vue, and local settings default to DEBUG=1.
A production deployment needs separate settings, DEBUG=0, HTTPS, secure session
and CSRF cookies, a production application server/reverse proxy, frontend asset
hosting, secrets management, trusted-ingress and throttle tuning, tested SMTP delivery, and
backups. `npm run build` verifies compilation; it does not deploy the application.
