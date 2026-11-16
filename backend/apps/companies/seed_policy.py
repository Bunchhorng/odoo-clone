"""Stable, owner-approved baseline access policy for company system groups.

This is data only: it does not enable endpoint enforcement.  Stage 4 will
consume the same canonical app keys when the endpoint registry is introduced.
"""
from dataclasses import dataclass


CANONICAL_APP_KEYS = (
    "dashboard", "contacts", "products", "product-categories", "crm",
    "sales", "purchase", "inventory", "invoicing", "accounting",
    "projects", "tasks", "employees", "helpdesk", "timesheets",
    "settings", "team",
)


@dataclass(frozen=True)
class SeedRight:
    app_key: str
    actions: frozenset[str]
    scope: str = "all_company"
    model_key: str = "*"


@dataclass(frozen=True)
class SeedGroup:
    system_key: str
    name: str
    code: str
    rights: tuple[SeedRight, ...]


READ_CREATE_WRITE = frozenset({"read", "create", "write"})
READ_WRITE = frozenset({"read", "write"})
READ_ONLY = frozenset({"read"})

# Delete is intentionally limited to inventory, which owns the current
# warehouse/location DELETE routes. Approve remains explicit and strict.
ADMIN_RIGHTS = (
    *(SeedRight(app, READ_CREATE_WRITE) for app in (
        "contacts", "products", "product-categories", "crm", "sales",
        "purchase", "inventory", "invoicing", "accounting", "projects",
        "tasks", "employees", "helpdesk", "timesheets",
    )),
    SeedRight("inventory", frozenset({"read", "create", "write", "delete"})),
    *(SeedRight(app, frozenset({"read", "create", "write", "approve"})) for app in (
        "sales", "purchase", "invoicing", "helpdesk", "timesheets",
    )),
    SeedRight("dashboard", READ_ONLY),
    SeedRight("settings", READ_WRITE),
    SeedRight("team", READ_CREATE_WRITE),
)

# One right row exists per app, so consolidate overlapping Admin actions above.
def _consolidate(rights: tuple[SeedRight, ...]) -> tuple[SeedRight, ...]:
    combined: dict[tuple[str, str, str], set[str]] = {}
    for right in rights:
        combined.setdefault((right.app_key, right.scope, right.model_key), set()).update(right.actions)
    return tuple(
        SeedRight(app_key, frozenset(actions), scope, model_key)
        for (app_key, scope, model_key), actions in combined.items()
    )


SYSTEM_GROUPS = (
    SeedGroup("admin", "Administrators", "system-admin", _consolidate(ADMIN_RIGHTS)),
    SeedGroup("member", "Members", "system-member", (
        SeedRight("dashboard", READ_ONLY),
        SeedRight("contacts", READ_ONLY),
        SeedRight("products", READ_ONLY),
        SeedRight("product-categories", READ_ONLY),
        SeedRight("projects", READ_ONLY),
        # AppRecordRule currently has no action column. Assigned therefore
        # applies to both task reads and writes; it cannot express broad read
        # plus assigned-only write yet.
        SeedRight("tasks", READ_WRITE, "assigned", "business.task"),
        SeedRight("timesheets", READ_CREATE_WRITE, "own", "business.timesheetentry"),
        SeedRight("helpdesk", READ_CREATE_WRITE, "own", "business.helpdeskticket"),
        SeedRight("helpdesk", READ_WRITE, "assigned", "business.helpdeskticket"),
        # Message visibility is derived from the parent ticket's owner in the
        # future record-rule adapter; messages themselves have no user FK.
        SeedRight("helpdesk", READ_CREATE_WRITE, "own", "business.ticketmessage"),
    )),
)


# Draft only. It is deliberately not consulted by any view until Stage 4.
CATALOG_APP_KEY_DRAFT = {
    "contacts": "contacts",
    "products": "products",
    "product-categories": "product-categories",
    "opportunities": "crm",
    "projects": "projects",
    "tasks": "tasks",
    "employees": "employees",
    "departments": "employees",
}
