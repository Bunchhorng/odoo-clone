# Docker + ERP Core + Authentication

This guide records the foundation milestone. The later
[Contacts/Products phase](CONTACTS-PRODUCTS.md) extends the catalog and shared Vue
components; [VERIFICATION.md](VERIFICATION.md) holds current suite totals.

This phase hardens the existing ERP foundation. It closes audit findings A-01
through A-05, adds account password change/recovery and shared authentication
throttles, and verifies startup with new Docker volumes. It does not add the
remaining Odoo applications or a public production deployment.

## 1. Start the project

Start Docker Desktop. From the project root on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

On Linux/macOS, prepare `.env` as explained in [SETUP.md](../SETUP.md), then:

```sh
docker compose up -d --build --wait --wait-timeout 300
docker compose ps
```

Existing `.env` secrets are preserved. The backend applies committed migrations,
including the authentication throttle and recovery-queue tables. A new clone still
needs its own `.env` secrets. Startup does not create or reset account passwords.

There are four services:

| Service | Purpose | Expected state |
| --- | --- | --- |
| db | MySQL, application records, sessions, authentication limits and recovery queue | Healthy |
| backend | Django APIs, administration, migrations | Healthy |
| frontend | Vue/Vite with same-origin API proxy | Healthy |
| mailer | Processes queued recovery mail and clears expired transient auth records | Running |

The mailer shares the backend's source/configuration and has no published port.
It starts after the backend is healthy. It has a restart policy, but no separate
worker heartbeat/health endpoint; Running is not proof of SMTP delivery.

Open <http://localhost:5173/login>, or the frontend port configured in `.env`.
This workspace's backend uses port 8001; fresh examples default to 8000.

For the first account only:

```sh
docker compose exec backend python manage.py createsuperuser
```

Sign in, create/select a company, and follow [ERP-GUIDE.md](ERP-GUIDE.md).
Account provisioning remains administrator-controlled; public registration and
invitation emails are not implemented.

## 2. Change your password

Select your email in the account bar, or open `/account`.

1. Enter the current password.
2. Enter and confirm a new password.
3. Select **Change password**.

Django validates length, common passwords, similarity to account information,
numeric-only passwords, and confirmation. The current session is rotated and stays
signed in; other sessions must sign in again. Login email matching is case-insensitive.
Passwords may contain spaces; API parsing does not trim them.

## 3. Recover a forgotten password

1. On Sign in, select **Forgot your password?**
2. Enter the account email and request a reset link.
3. Open the emailed link and set/confirm a new password.
4. Sign in normally with the new password.

The request response is identical for eligible, unknown, inactive and unusable-
password accounts. The HTTP endpoint queues the request and performs no account
lookup or SMTP work. The mailer checks eligibility at delivery time. Only active
accounts with usable passwords receive a link.

Reset links use Django's signed token generator, expire after 30 minutes, and become
invalid after use/password change. Concurrent reuse is serialized on the user row.
Reset invalidates existing sessions and ends the requesting browser session; it
does not automatically log the user in.

The token is placed in a URL fragment so it does not enter HTTP access-log paths,
then removed from the visible URL/history by the reset screen. Reloading that
screen requires opening the complete email link again.

### Local recovery mail

The default console mail backend writes messages to the mailer container log. To
read a reset link you explicitly requested during local development:

```sh
docker compose logs --tail=100 mailer
```

Reset links are bearer secrets; keep those logs private. No real email is sent by
the default backend. Automated tests use in-memory email and temporary accounts.
The browser smoke check refuses an SMTP backend so it cannot send real messages.

To process pending mail once without the worker loop:

```sh
docker compose exec backend python manage.py process_auth_mail
```

The worker retries delivery failures up to three times with 30/60-second delays.
Queued requests expire after 15 minutes. Processed jobs are retained for up to
one day, and expired rate buckets are cleaned periodically. This is an at-least-
once delivery queue: a process crash after SMTP acceptance can send a duplicate
email, while the reset token still has single-use password-change semantics.

### Configure SMTP deliberately

In the private `.env`, set:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=your-smtp-host
EMAIL_PORT=587
EMAIL_HOST_USER=your-smtp-user
EMAIL_HOST_PASSWORD=your-smtp-password
EMAIL_USE_TLS=1
DEFAULT_FROM_EMAIL=your-approved-sender@example.com
```

Then recreate the two Python services:

```sh
docker compose up -d backend mailer
```

`FRONTEND_ORIGIN` controls reset-link origin and is never taken from request headers
or an arbitrary client redirect. Compose defaults it to the local frontend port;
an optional override must be a single HTTP(S) origin with no path/credentials/query.
External SMTP delivery was not integration-tested in this phase.

## 4. Authentication limits and sessions

Limits live in MySQL and are shared across backend processes. Login aliases that
match one database account share its stored identity. Recovery delivery also has
a per-recipient budget, so database-collation aliases cannot bypass it. Transport
retries use the original queued request's slot. Their database keys
are HMACs instead of raw account emails or IPs. Throttled responses return JSON
HTTP **429** with **Retry-After**. Successful login clears its account bucket;
the IP budget remains. Existing authenticated sessions are not locked out by failed
login attempts.

| Setting | Default | Meaning |
| --- | --- | --- |
| AUTH_RATE_WINDOW_SECONDS | 900 | Fixed attempt window, 15 minutes |
| AUTH_LOGIN_IDENTITY_LIMIT | 10 | Login attempts per case-insensitive email |
| AUTH_LOGIN_IP_LIMIT | 100 | Login attempts per direct network peer |
| AUTH_RESET_IDENTITY_LIMIT | 3 | Reset requests per case-insensitive email |
| AUTH_RESET_IP_LIMIT | 30 | Reset requests per direct network peer |
| SESSION_COOKIE_AGE | 28800 | Django session-cookie lifetime, 8 hours |

Password change allows five attempts per user/window. Reset confirmation uses the
login IP budget value in a separate bucket. These controls supplement, rather than
replace, the session/CSRF and company-access rules.

`X-Forwarded-For` is intentionally not trusted. In the local Vite proxy setup,
the peer can be the frontend container, so clients share its IP budget. A public
deployment needs an explicit trusted-ingress policy and suitable limits. There is
no CAPTCHA, MFA, SSO, distributed edge protection or universal abuse-prevention claim.

## 5. ERP core fixes

| Audit finding | Fixed behavior | Verification |
| --- | --- | --- |
| A-01 | Dirty quotations/RFQs/invoices/bills block Confirm/Issue until Save or Discard. Route changes, company switches and sign-out can be cancelled; browser reload/close warns about dirty document forms. | Browser regression covers all four document kinds, cancelled navigation/company change/sign-out, and explicit saves |
| A-02 | Lists reset to page one on company/filter changes. The server clamps out-of-range pages and the client adopts the returned page. | API and browser: 25 contacts on page two to a company with one contact |
| A-03 | A repeated payment UUID returns its financial record without emitting another payment completion event. | Sequential and concurrent API tests plus browser retry |
| A-04 | Record IDs must use bounded ASCII decimal digits and fit the positive database range. | Invalid Unicode, huge strings, booleans, arrays and negative/out-of-range IDs return JSON 400 |
| A-05 | Forms display retained inactive relations and send changed fields. Retaining an existing relationship does not require reactivation; newly selected relationships still need active/company-valid targets. | API and browser edits after teammate deactivation; foreign-company/new inactive links still rejected |

Confirmed records remain immutable through normal APIs. Numbering, stock checks and
payment checks remain transactional. The phase does not add optimistic version
checks for simultaneous editors, partial delivery/invoicing, reversals, or accounting.

## 6. Run the checks

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
node scripts/verify-browser.mjs
```

The first command checks Compose configuration, Python dependency consistency,
Django settings/migrations, all backend tests, and the Vue build. The optional
second command requires host Node.js 22+ and Microsoft Edge on Windows. It creates
temporary accounts/companies, exercises real workflows, and cleans up its own
business records and recovery requests. It never changes your account password.

The browser reset check generates a token for its temporary test account through
the local operator test helper. Backend tests separately verify queued email content,
eligibility, retries, expiry, CSRF and token reuse. The browser test is not a test
of an external SMTP provider or a saved PDF.

## 7. CI and fresh Docker verification

Run a repeatable fresh-volume check without touching your normal project:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check-fresh.ps1
```

This generates a unique Compose project, temporary secrets and available host ports,
starts new volumes, runs the backend suite/build/proxy check, verifies its volume
labels, and removes only its own containers, volumes and generated configuration.
It requires Docker and PowerShell; host Python/Node are not needed. If any volume
ownership check fails, it stops cleanup for inspection rather than deleting it.

`.github/workflows/check.yml` builds a new Compose stack, applies migrations,
checks dependencies/schema, runs backend tests, and compiles Vue on pushes/PRs.
It uses read-only repository permissions, disabled persisted checkout credentials,
an immutable checkout-action revision, disposable configuration, and runner-only
volume cleanup. Its backend/test/build commands were validated locally. Hosted
GitHub execution remains unverified until the reviewed files are committed/pushed.

On **2026-10-28 (Asia/Bangkok)** this phase passed:

- **78 backend tests**, including concurrent throttling, reset-token reuse,
  overselling, overpayment, payment retries, and last-owner protection.
- **16 browser workflow groups**, including the five original audit regressions
  and self-service password change/reset.
- Vue compilation, dependency consistency, migration consistency and the API proxy
  health path in a separate Compose project with **new MySQL/dependency volumes**.
- Rebuild/startup while preserving the existing private `.env`.

This verifies fresh containers/volumes from the current working tree, not a clean
checkout of the old starter commit. The temporary verification stack was removed
after its checks. The main local ERP stack and data were retained.

## Remaining release work

The stack still uses development servers/local settings. Production settings,
HTTPS/secure-cookie configuration, a trusted proxy policy, delivery monitoring,
backup/restore, external mail integration validation and per-app permissions remain.
Public registration, account invitations, MFA and SSO also remain outside this phase.
See [the updated parity matrix](ODOO-PARITY-MATRIX.md).

References: [Django 5.2 authentication and password reset](https://docs.djangoproject.com/en/5.2/topics/auth/default/),
[OWASP authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html),
[OWASP password recovery](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html),
and [the official checkout action](https://github.com/actions/checkout).
