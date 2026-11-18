"""Create-missing-only baseline access seeding and role/group synchronization."""
from django.db import IntegrityError

from .models import (
    AppAccessRight, AppRecordRule, CompanyAccessGroup,
    CompanyAccessGroupMembership,
)
from .seed_policy import SYSTEM_GROUPS


def _available_code(company, group_model, base_code):
    code, suffix = base_code, 2
    while group_model.objects.filter(company=company, code=code).exists():
        code = f"{base_code}-{suffix}"
        suffix += 1
    return code


def seed_company_records(company, group_model, right_model, rule_model):
    """Seed one company using supplied model classes (safe for data migrations)."""
    groups = {}
    for definition in SYSTEM_GROUPS:
        group = group_model.objects.filter(company=company, system_key=definition.system_key).first()
        if group is None:
            group = group_model.objects.create(
                company=company,
                name=definition.name,
                code=_available_code(company, group_model, definition.code),
                system_key=definition.system_key,
                is_system=True,
            )
        groups[definition.system_key] = group
        for right in definition.rights:
            defaults = {f"can_{action}": action in right.actions for action in (
                "read", "create", "write", "delete", "approve",
            )}
            right_model.objects.get_or_create(
                company=company, group=group, app_key=right.app_key, defaults=defaults,
            )
            rule_model.objects.get_or_create(
                company=company, group=group, app_key=right.app_key,
                model_key=right.model_key, scope=right.scope,
            )
    return groups


def sync_membership_records(membership, groups, group_membership_model):
    """Replace only this membership's Admin/Member system memberships."""
    system_groups = [groups[key] for key in ("admin", "member")]
    group_membership_model.objects.filter(user_id=membership.user_id, group__in=system_groups).delete()
    target_key = {"admin": "admin", "member": "member"}.get(membership.role)
    if target_key:
        group_membership_model.objects.get_or_create(group=groups[target_key], user_id=membership.user_id)


def seed_company(company):
    return seed_company_records(company, CompanyAccessGroup, AppAccessRight, AppRecordRule)


def sync_membership_system_groups(membership):
    groups = seed_company(membership.company)
    sync_membership_records(membership, groups, CompanyAccessGroupMembership)
    return groups
