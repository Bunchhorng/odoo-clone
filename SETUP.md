# Part 04 — Project Setup Guide

## 1. Prepare your machine

Install and start Docker Desktop (Windows: WSL2 engine recommended), or Docker Engine and Compose plugin on Linux. Check:

```bash
docker --version
docker compose version
docker info
```

If Docker daemon isn't running, first start Docker Desktop or the Docker service. Members do **not** need local Python/Node/MySQL.

## 2. Obtain repository

As team lead, extract this starter into a new `kerp` Git repository and push it to GitHub. Team members clone it. Do not commit the archive itself or local `.env`.

## 3. Configure environment

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Change the three `REPLACE_WITH_...` values (Django secret key, MySQL app password, MySQL root password). Use different strong random passwords. `MYSQL_HOST` is set to `db` *inside* the backend container; don't use `localhost` there.

## 4. Start all services

```bash
docker compose up -d --build
docker compose ps
```

There should be `db`, `backend`, and `frontend`. Compose waits for the MySQL healthcheck before starting Django. Django applies committed migrations before starting its development server. The MySQL first-run init script grants the application user rights on an isolated Django test database only; do not use `down -v` as a repair shortcut if the database has valuable data.

## 5. Verify API, DB, Vue

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py showmigrations
docker compose exec backend python manage.py test
```

Visit:
- `http://localhost:8000/api/v1/health/` — Django + database.
- `http://localhost:5173/api/v1/health/` — Vue dev proxy → Django.
- `http://localhost:5173` — app launcher; connection badge should be green.

## 6. Create one admin user

```bash
docker compose exec backend python manage.py createsuperuser
```

Enter an email address and password; the custom User model uses email rather than username. Sign in at `http://localhost:8000/admin/`, then optionally add a Company and Company Membership.

## 7. Create feature branches

```bash
git checkout -b feat/core-auth
```

Later, only Django model changes need new migration files:

```bash
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
```

Never independently modify the same migration in parallel branches. Coordinate merge order.

## Definition of Done for Part 04

- Every teammate can run Docker Compose from a clone.
- All 3 containers start and database becomes healthy.
- Django migration history is current, including custom User and Company models.
- Django health endpoint responds via ports 8000 and 5173.
- Vue shows API status `connected`.
- Lead creates admin user and signs in to Django Admin.
- Django automated tests pass.
- Repository `.env` is not tracked.

## Security note

All ports are bound to 127.0.0.1, and Django runs `DEBUG=1` via local settings. **This is a development setup, not a production deployment.** Before production, separate settings, use a real WSGI/ASGI application server and reverse proxy, HTTPS, `DEBUG=0`, secret management and storage/backups.


Project Structure

KERP-ERP/
├── backend/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── companies/
│   │   └── core/
│   ├── config/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── manage.py
│
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── data/
│   │   ├── router/
│   │   ├── services/
│   │   ├── stores/
│   │   ├── views/
│   │   └── App.vue
│   ├── Dockerfile
│   └── package.json
│
├── infrastructure/
├── docs/
│   ├── databaseDesign/
│   ├── ui-ux/
│   ├── SETUP.md
│   ├── TEAM-WORKFLOW.md
│   └── ROADMAP.md
│
├── compose.yml
├── .env.example
├── .gitignore
└── README.md