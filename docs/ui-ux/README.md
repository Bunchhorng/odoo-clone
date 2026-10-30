# KERP interface documentation

The frontend uses a shared purple KERP shell, company context, app launcher,
module navigation, reusable ERP views and light/dark themes. Existing Vue routes,
session authentication, CSRF protection and company-scoped APIs are retained.

- [Source audit and issues](AUDIT.md)
- [Implementation report covering all nine phases](IMPLEMENTATION-REPORT.md)
- [Design tokens, component contracts, affected routes and keyboard behavior](DESIGN-SYSTEM.md)
- [Executed checks and verification limits](../testing/UI-VERIFICATION.md)
- [Review groups and team workflow](../teamManagement/UI-WORKFLOW.md)

All 14 registered applications have implemented routes and business features.
A green health probe confirms API/database connectivity only. Application errors
are reported independently. Availability follows active company membership;
owner/admin write restrictions remain enforced on the server. The app registry
also supports non-actionable coming-soon entries for future unfinished apps.

The notification control shows real recent company activity. It has no fabricated
unread count, email action or dismiss state. Backend contracts for per-app
entitlements and an unread notification inbox do not currently exist.

For existing module workflows see [ERP-GUIDE.md](../ERP-GUIDE.md),
[CONTACTS-PRODUCTS.md](../CONTACTS-PRODUCTS.md) and
[VUE-COMPONENTS.md](../VUE-COMPONENTS.md).
