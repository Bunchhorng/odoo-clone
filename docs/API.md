# API reference: login and company access

Business modules have a separate [ERP API reference](ERP-API.md).

Base URL through Vue: `/api/v1/`. All API writes use Django CSRF protection,
including login. Use cookies from the same origin; these are session APIs, not
Bearer-token APIs. Responses with user/company data use `Cache-Control: private,
no-store`.

## Browser example

Run this from the Vue page's browser console with your own credentials:

```javascript
await fetch('/api/v1/auth/session/', { credentials: 'same-origin' })
const csrf = () => decodeURIComponent(document.cookie.split('; ')
  .find(cookie => cookie.startsWith('csrftoken='))?.slice(10) || '')
const response = await fetch('/api/v1/auth/login/', {
  method: 'POST',
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
  body: JSON.stringify({ email: 'you@example.com', password: 'your-password' }),
})
console.log(await response.json())
```

Login rotates the CSRF token. Read the cookie again before each following write.
The application does this automatically in `frontend/src/services/api.js`.

## Endpoints

| Method | Path | Access | Result |
| --- | --- | --- | --- |
| GET | `health/` | Public | Database-backed health status |
| GET | `auth/session/` | Public | Current session and CSRF cookie |
| POST | `auth/login/` | Public + CSRF | Authenticate email/password |
| POST | `auth/logout/` | Signed in + CSRF | End the session |
| POST | `auth/password/change/` | Signed in + CSRF | Change password and keep this session |
| POST | `auth/password/reset/` | Public + CSRF | Queue a generic recovery request |
| POST | `auth/password/reset/confirm/` | Public + CSRF | Validate a signed token and set a new password |
| GET | `companies/` | Signed in | Active companies with active memberships |
| POST | `companies/` | Signed in + CSRF | Create a company and owner membership |
| POST | `companies/{company_id}/select/` | Active company membership + CSRF | Save selected company |
| GET | `companies/{company_id}/members/` | Active company membership | View all company memberships |
| POST | `companies/{company_id}/members/` | Owner or admin + CSRF | Add an existing active account |
| PATCH | `companies/{company_id}/members/{membership_id}/` | Owner or admin + CSRF | Change role or membership active flag |

`membership_id` is the membership's ID, which may differ from `user_id`.
Create/add return 201. Other successful responses return 200.

## Session response

```json
{
  "user": {"id": 1, "email": "you@example.com", "name": "you@example.com", "is_staff": false},
  "companies": [{"id": 4, "name": "Example Studio", "slug": "example-studio-ab12cd34", "role": "owner"}],
  "active_company_id": 4
}
```

Anonymous sessions return `user: null`, `companies: []`, and
`active_company_id: null`. Login, company creation, and selection return a session
response. Logout returns an anonymous session response. If the selected company is
no longer accessible, session retrieval chooses the first accessible company by
name/ID, or null if there are none. The user name falls back to their email.

## Request bodies

Login:

```json
{"email": "you@example.com", "password": "your-password"}
```

Create company (trimmed name, 1–200 characters; slug is generated):

```json
{"name": "Example Studio"}
```

Add a teammate (role defaults to member):

```json
{"email": "teammate@example.com", "role": "member"}
```

Update membership (provide either or both fields; active must be a JSON boolean):

```json
{"role": "admin", "is_active": true}
```

Select company and logout need no request body. Endpoints with defined JSON bodies
reject unknown fields.

## Team response

GET returns `{"members": [...]}`. Add/update return `{"member": {...}}`.
Each membership has this shape:

```json
{
  "id": 7,
  "user_id": 2,
  "email": "teammate@example.com",
  "name": "teammate@example.com",
  "role": "member",
  "is_active": true,
  "user_is_active": true
}
```

All members of the selected company can read its team, including disabled
membership rows. Owners manage all roles. Administrators may only add/update
ordinary members; they cannot promote anyone or update an admin/owner row, including
their own. Members cannot write. At least one active owner with an active user
account must remain. An inactive account cannot be added.

## Errors

Errors are JSON with an `error` message. A missing/invalid CSRF token is checked by
middleware before the view, so an unauthenticated write without a token can return
403 before authentication is evaluated.

| Status | Meaning |
| --- | --- |
| 400 | Invalid JSON, fields, role, email, missing account, or invalid values |
| 401 | Sign-in required, invalid credentials, or disabled account at login |
| 403 | CSRF failure or insufficient role |
| 404 | Company inaccessible/not found, or membership not in that company |
| 405 | Method not supported; response includes Allow header |
| 409 | Duplicate membership/record or attempt to remove the last active owner |
| 415 | Request body is not application/json |
| 429 | Authentication limit reached; Retry-After contains seconds to wait |

An active company ID in the session does not bypass membership checks. All
company/member URLs enforce access independently.

## Password change and recovery

Change body:

```json
{"old_password":"current-password","new_password1":"new-strong-password","new_password2":"new-strong-password"}
```

The current session is rotated and remains signed in; other sessions become invalid.
Wrong current password, weak/mismatched passwords, and invalid field types return
400. Passwords retain whitespace, allow up to 1024 characters, and use Django's
configured validators.

Recovery-request body:

```json
{"email":"you@example.com"}
```

Every valid email format receives the same generic 200 message unless throttled.
The worker checks account eligibility later. The response never includes a user ID,
reset token, or delivery status.

Recovery-confirmation body:

```json
{"uid":"base64-user-id","token":"signed-token","new_password1":"new-strong-password","new_password2":"new-strong-password"}
```

Tokens expire after 30 minutes and become invalid after use/password change. Invalid,
expired, inactive-account, and foreign-user tokens return generic JSON 400 errors.
Success invalidates existing sessions, ends this browser's session, and requires a
normal sign-in. Concurrent reuse is serialized on the user row.

All endpoints require CSRF. Login, recovery and password change have shared MySQL
limits; 429 includes Retry-After. The reset screen reads a token from the email URL
fragment, removes it from history, and submits it in the CSRF-protected body.
See [FOUNDATION.md](FOUNDATION.md) for defaults, worker retries and proxy limits.
