# Database foundation

- `accounts.User`: Django's standard authentication fields with a unique email instead of a username.
- `companies.Company`: name, unique slug, active flag, and timestamps.
- `companies.CompanyMembership`: company, user, role, active flag, and creation timestamp.

One user can belong to multiple companies. Each company/user pair is unique.
Deleting a user or company removes its memberships. Roles are `owner`, `admin`,
and `member`; their application authorization behavior is future feature work.

The development application database is `MYSQL_DATABASE`. Django tests use the
separate `test_<MYSQL_DATABASE>` database with privileges scoped to that exact name.
