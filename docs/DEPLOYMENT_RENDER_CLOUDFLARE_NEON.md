# Production deployment: Render, Cloudflare, and Neon

This repository now includes a Render Blueprint in [`render.yaml`](../render.yaml)
for this topology:

```text
Browser
  |  https://app.example.com              https://api.example.com
  v                                               |
Cloudflare DNS/proxy -----------------------------+
  |                                               |
Render static site (Vue)                  Render web service (Django/Gunicorn)
                                                  |
                                           Neon pooled PostgreSQL
                                                  |
                                  Render background worker (password-reset mail)
```

Use two HTTPS subdomains of the same Cloudflare zone, such as
`app.example.com` and `api.example.com`. This is required by the session-based
authentication design: Django sets cookies for `.example.com`, and the Vue app
can then send them to the API with CORS credentials. Do not put the frontend and
API on unrelated registrable domains.

## Before you start

- Use a new, empty Neon database. The app's current local database is MySQL;
  `migrate` creates PostgreSQL schema but **does not transfer MySQL data**.
  Back up and plan a tested data migration separately if the local database
  contains data you need to retain.
- Commit the deployment files to the Git repository connected to Render. Never
  commit Neon URLs, SMTP passwords, or an exported `.env` file.
- The Blueprint uses Render's `0.5c-512mb` web/worker plan because its
  pre-deploy migration command requires a paid web service. Keep the worker: it
  delivers the queued password-reset emails.

## 1. Create Neon database credentials

Create a Neon project in a region near the Render region (the Blueprint uses
Singapore). In Neon, copy the **pooled** connection string and keep
`sslmode=require`, for example:

```text
postgresql://USER:PASSWORD@ep-example-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
```

Use this as `DATABASE_URL` only in Render. The production settings select
PostgreSQL when `DJANGO_SETTINGS_MODULE=config.settings.production`; local Docker
development remains on MySQL. The local Docker image installs
`requirements.local.txt`, while Render installs the PostgreSQL-only
`requirements.txt`.

## 2. Create the Render Blueprint

In Render, select **New > Blueprint**, connect this repository, and select
`render.yaml`. If `kerp-api`, `kerp-web`, or `kerp-auth-mailer` are already used
in the Render workspace, rename them consistently in `render.yaml` before
creating the Blueprint.

Enter these values when Render prompts for the API service variables. Replace
the examples with your actual domain:

| Variable | Example value | Notes |
| --- | --- | --- |
| `DATABASE_URL` | Neon pooled PostgreSQL URL | Secret; retain `sslmode=require`. |
| `DJANGO_ALLOWED_HOSTS` | `api.example.com,.onrender.com` | Keep `.onrender.com` so Render health checks work. |
| `FRONTEND_ORIGIN` | `https://app.example.com` | No trailing slash. |
| `DJANGO_CORS_ALLOWED_ORIGINS` | `https://app.example.com` | Exact, comma-separated origins only. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://app.example.com` | Exact, comma-separated origins only. |
| `DJANGO_COOKIE_DOMAIN` | `.example.com` | The shared parent domain, including its leading dot. |
| `DEFAULT_FROM_EMAIL` | `KERP <noreply@example.com>` | A verified sender for your SMTP provider. |
| `EMAIL_HOST` | `smtp.example-mail.com` | SMTP hostname. |
| `EMAIL_HOST_USER` | `smtp-user` | SMTP account or API user. |
| `EMAIL_HOST_PASSWORD` | SMTP secret | Secret. |
| `VITE_BACKEND_ORIGIN` | `https://api.example.com` | Enter for the `kerp-web` static-site service; it is public and compiled into the Vue build. |

Render generates `DJANGO_SECRET_KEY` and securely shares it with the mail worker.
It also runs `migrate` before each API release, builds Django admin static assets,
and checks `/api/v1/health/` before routing traffic. The mail worker waits until
the migration check succeeds before it begins polling the queue.

The supplied blueprint intentionally does not create a Render database: Neon is
the database provider. Render's Blueprint variables support secure prompts and
cross-service references; static-site rewrites send Vue Router paths to
`index.html`. See Render's [Blueprint reference](https://render.com/docs/blueprint-spec)
and [static-site rewrite guide](https://render.com/docs/redirects-rewrites).

## 3. Attach domains and configure Cloudflare

In Render, add `api.example.com` to **kerp-api** and `app.example.com` to
**kerp-web**. Render will show each service's `onrender.com` target.

In Cloudflare DNS, remove conflicting records (especially `AAAA` records), then
create these CNAME records initially as **DNS only**:

| Name | Target | Service |
| --- | --- | --- |
| `api` | the `kerp-api` `onrender.com` hostname | Django API |
| `app` | the `kerp-web` `onrender.com` hostname | Vue static site |

Verify both domains in Render and wait until its certificates are issued. Then
you may switch the two records to **Proxied** (orange cloud). In Cloudflare set
**SSL/TLS > Overview** to **Full (strict)**. Never use Flexible SSL: it leaves
Cloudflare-to-Render traffic unencrypted and conflicts with Django's HTTPS-only
cookies. Render's current Cloudflare instructions require DNS-only records during
initial domain verification, followed by optional proxying after certificates are
valid. See [Render's Cloudflare DNS guide](https://render.com/docs/configure-cloudflare-dns)
and Cloudflare's [encryption mode documentation](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/).

Add a Cloudflare cache rule to bypass cache for `api.example.com/api/*` (and
`api.example.com/admin/*`). Do not cache authenticated API responses. The Vue
static site is safe to cache normally.

## 4. Verify the live release

After the API and worker are both live, check:

```powershell
curl.exe -i https://api.example.com/api/v1/health/
curl.exe -i -H "Origin: https://app.example.com" https://api.example.com/api/v1/auth/session/
```

The first request must return HTTP 200 and JSON with `"database": "connected"`.
The second must return the exact `Access-Control-Allow-Origin` value and
`Access-Control-Allow-Credentials: true`, as well as a `csrftoken` cookie scoped
to `.example.com` with `Secure` enabled. Then use an incognito browser session to
register, sign in, create a company, sign out, and request a password reset. The
Render `kerp-auth-mailer` logs should show it staying healthy while it polls.

Run a final deploy check from the API service shell or a matching local production
environment:

```sh
python manage.py check --deploy
```

`security.W021` can remain if you deliberately do not enable HSTS preload. Do
not enable preload until every current and future subdomain of the parent domain
is HTTPS-only; browsers cache that decision for a long time.

## Operations

- Use Neon's backups, branches, and restore process for database recovery. Test
  restoration before relying on it.
- Keep the Neon password, SMTP credentials, and `DJANGO_SECRET_KEY` only in
  Render's encrypted environment variables. Rotating the Django secret logs out
  all users and invalidates outstanding reset tokens.
- Apply schema changes through a normal Render API deployment. Do not run
  `makemigrations` in production; commit reviewed migration files first.
- Restrict `DJANGO_CORS_ALLOWED_ORIGINS` and `DJANGO_CSRF_TRUSTED_ORIGINS` to
  trusted application origins. Do not use `*` with credentialed requests.
