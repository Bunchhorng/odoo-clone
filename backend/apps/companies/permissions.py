"""Server-side, Odoo-inspired application-access resolution.

This module contains the only implied-access policy. Endpoint enforcement is
introduced later behind the configured rollout mode.
"""
from dataclasses import dataclass
from typing import FrozenSet

from .models import AppAccessRight, AppRecordRule, CompanyAccessGroupMembership, CompanyMembership, UserAppAccessOverride

ACTIONS = ("read", "create", "write", "delete", "approve")

# Read-only dependencies. A direct revoke on the implied target still wins.
IMPLIED_READ_ACCESS = {
    "sales": frozenset({"contacts", "products", "product-categories"}),
    "purchase": frozenset({"contacts", "products", "product-categories"}),
    "invoicing": frozenset({"contacts", "products", "product-categories"}),
    "crm": frozenset({"contacts"}),
}

# Only models with a real owner/requester or assignee can use narrowed scopes.
RECORD_SCOPE_CAPABILITIES = {
    ("timesheets", "business.timesheetentry"): frozenset({"all_company", "own"}),
    ("helpdesk", "business.helpdeskticket"): frozenset({"all_company", "own", "assigned"}),
    ("helpdesk", "business.ticketmessage"): frozenset({"all_company", "own"}),
    ("projects", "business.task"): frozenset({"all_company", "assigned"}),
}


class NoActiveMembership(PermissionError):
    pass


def record_scope_supported(app_key: str, model_key: str, scope: str) -> bool:
    return scope in RECORD_SCOPE_CAPABILITIES.get((app_key, model_key), frozenset({"all_company"}))


@dataclass(frozen=True)
class EffectiveAccess:
    company_id: int
    user_id: int
    permissions: dict[str, FrozenSet[str]]
    record_scopes: dict[tuple[str, str], FrozenSet[str]]

    def allows(self, app_key: str, action: str) -> bool:
        return action in self.permissions.get(app_key, self.permissions.get("*", frozenset()))

    def scopes_for(self, app_key: str, model_key: str) -> FrozenSet[str]:
        return self.record_scopes.get((app_key, model_key), self.record_scopes.get((app_key, "*"), self.record_scopes.get(("*", "*"), frozenset())))


def _active_membership(user, company_id):
    membership = CompanyMembership.objects.filter(
        company_id=company_id, user=user, is_active=True, company__is_active=True,
    ).first()
    if membership is None:
        raise NoActiveMembership("An active company membership is required.")
    return membership


def resolve_effective_access(user, company_id: int) -> EffectiveAccess:
    """Resolve additive group grants; explicit user revokes take precedence."""
    membership = _active_membership(user, company_id)
    if membership.role == CompanyMembership.Role.OWNER:
        return EffectiveAccess(
            company_id=company_id,
            user_id=user.pk,
            permissions={"*": frozenset(ACTIONS)},
            record_scopes={("*", "*"): frozenset({AppRecordRule.Scope.ALL_COMPANY})},
        )

    group_ids = CompanyAccessGroupMembership.objects.filter(
        user=user, group__company_id=company_id, group__is_active=True,
    ).values_list("group_id", flat=True)
    permissions: dict[str, set[str]] = {}
    for right in AppAccessRight.objects.filter(company_id=company_id, group_id__in=group_ids):
        granted = permissions.setdefault(right.app_key, set())
        for action in ACTIONS:
            if getattr(right, f"can_{action}"):
                granted.add(action)

    scopes: dict[tuple[str, str], set[str]] = {}
    for rule in AppRecordRule.objects.filter(company_id=company_id, group_id__in=group_ids):
        scopes.setdefault((rule.app_key, rule.model_key), set()).add(rule.scope)

    overrides = {item.app_key: item for item in UserAppAccessOverride.objects.filter(company_id=company_id, user=user)}
    for source_app, targets in IMPLIED_READ_ACCESS.items():
        if "read" not in permissions.get(source_app, set()):
            continue
        for target in targets:
            if getattr(overrides.get(target), "can_read", None) is not False:
                permissions.setdefault(target, set()).add("read")
                scopes.setdefault((target, "*"), set()).add(AppRecordRule.Scope.ALL_COMPANY)

    for app_key, override in overrides.items():
        granted = permissions.setdefault(app_key, set())
        for action in ACTIONS:
            value = getattr(override, f"can_{action}")
            if value is True:
                granted.add(action)
            elif value is False:
                granted.discard(action)

    return EffectiveAccess(
        company_id=company_id,
        user_id=user.pk,
        permissions={app: frozenset(actions) for app, actions in permissions.items()},
        record_scopes={key: frozenset(values) for key, values in scopes.items()},
    )
