# Login and company access: user guide

For the business applications, follow the [ERP walkthrough](ERP-GUIDE.md).

This is the first completed module. Use it to sign in, create company workspaces,
switch between them, and control who can use each workspace. Run the project using
[SETUP.md](../SETUP.md) before following these steps.

## 1. Create the first account

In a terminal at the project root:

```powershell
docker compose exec backend python manage.py createsuperuser
```

Enter an email and a strong password when prompted. No default password is shipped.
If you already have an account, use it; do not run this command again for it.

Open <http://localhost:5175/login> and sign in with that email and password.
The account does not need Django staff permission to use KERP. Staff permission
is needed only to enter Django Admin.

## 2. Create your first company

1. Select **Companies** in the navigation.
2. Enter a company name, such as `Example Studio`.
3. Select **Create company**.

KERP creates the company, gives you its **owner** role, and selects it automatically.
Its unique internal slug is generated for you. Users may create multiple companies,
and companies may share a display name.

## 3. Prepare a teammate's account

An account and a company membership are different:

- The **account** identifies a person and holds their email and password.
- The **membership** gives that person a role within one company.

A Django administrator opens `/admin/` on the backend. The default address is
<http://localhost:8000/admin/>; this workspace may use port 8001 according to `.env`.
Under **Accounts > Users > Add**, create the teammate's email and password. Leave
staff and superuser permissions off for ordinary teammates. Share the credentials
privately; ask the administrator for password changes when needed.

Creating an account alone does not grant access to an existing company.

## 4. Add the teammate to your company

1. Check the company shown in **Working in** at the top of KERP.
2. Open **Team**.
3. Enter the teammate's existing account email under **Add a teammate**.
4. Choose their role and select **Add teammate**.

The teammate can sign in and select the company immediately. No invitation email
is sent. If they are already signed in, they should reload to refresh their company
list. Adding the same email twice gives a clear error; use the existing row to
reactivate someone whose company access was disabled.

## 5. Understand the roles

| Action within a company | Owner | Administrator | Member |
| --- | --- | --- | --- |
| View the team | Yes | Yes | Yes |
| Add an existing account as a member | Yes | Yes | No |
| Disable/reactivate member access | Yes | Yes | No |
| Add or change administrators and owners | Yes | No | No |
| Change their own privileged role | Yes, if another active owner remains | No | No |

Each user has one role per company. Being an owner in Company A gives no permission
in Company B. Django superusers still need memberships to use the application API.
Django Admin is a separate trusted administration tool with global access.

## 6. Switch companies

Use **Working in** at the top, or select **Switch company** on the Companies page.
The team screen reloads for the selected company. Your choice is kept in your
server session and survives a page reload. If access to that company is removed,
the next session refresh selects another accessible company, or no company.

Company access is checked by the server on every request. Changing a URL or a
company ID cannot grant access. Disabling a company or a membership removes access
to that company. Disabling an account in Django Admin prevents login and use of
its current session.

## 7. Change or remove access

On **Team**, change a role or clear **Active access**, then select **Save** on that
person's row. The account remains available for other companies. Select **Active
access** again and save to restore membership access.

At least one active owner with an active account must remain. To transfer ownership,
promote another active teammate to owner first, then change your own role. If the
other owner's account is disabled, it does not count as an active owner.

Django administrators can edit records directly outside these application rules.
When using Django Admin, retain at least one active owner for each active company.

## 8. Sign out and recover access

Select **Sign out**. Protected screens return you to sign-in, and the server session
is ended. If a session expires, KERP asks you to sign in again.

To change your own password, select your email in the account bar. For a forgotten
password, use **Forgot your password?** on sign-in. Local recovery messages appear
in the mailer log; [FOUNDATION.md](FOUNDATION.md) explains configuration and the
30-minute single-use links. An administrator can also reset an account from Django
Admin or run this interactive command:

```powershell
docker compose exec backend python manage.py changepassword person@example.com
```

Email invitations, self-registration, MFA and SSO remain future features.
See [the roadmap](ROADMAP.md).
