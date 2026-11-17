"""Rollout-safe endpoint permission checks.

`off` returns before touching the database.  `log` records would-be denials
and deliberately never alters a response.  `enforce` is retained for the
approved future rollout only.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings

from apps.core.api import APIError
from .access import owner_only_for
from .endpoint_registry import is_explicitly_public, rule_for
from .permissions import NoActiveMembership, resolve_effective_access

logger = logging.getLogger("kerp.permissions")


@dataclass(frozen=True)
class PermissionImpact:
    """A behavior that is observed in log mode and applied only in enforce."""
    reason: str
    hidden_records: int = 0
    value: object = None


def _company_id(kwargs):
    return kwargs.get("company_id")


def permission_enforced(request, company_id, impact_factory, *, action=None):
    """Evaluate a pending permission impact only outside off mode.

    `impact_factory` returns a PermissionImpact when an enforce-mode response
    would differ, or None when no restriction applies.  Log mode records that
    impact but deliberately returns None so callers keep their legacy response.
    """
    mode = settings.PERMISSION_MODE
    if mode == "off":
        return None
    impact = impact_factory()
    if impact is None:
        return None
    if mode == "log":
        _log_would_deny(request, company_id, impact.reason, impact.hidden_records, action=action)
        return None
    return impact


def audit_request(request, view, kwargs):
    mode = settings.PERMISSION_MODE
    if mode == "off" or is_explicitly_public(request.path_info):
        return
    try:
        rule = rule_for(view, request.method)
        if rule is None:
            raise RuntimeError("unmapped_route")
        if rule.membership_only or _company_id(kwargs) is None:
            return
        company_id = _company_id(kwargs)
        if rule.owner_only:
            owner_only_for(request.user, company_id)
            return
        access = resolve_effective_access(request.user, company_id)
        app_key, action = rule.resolve(request, kwargs)
        checks = ((app_key, action), *rule.extra)
        for target, required in checks:
            allowed = (any(access.allows(candidate, required) for candidate in target)
                       if isinstance(target, tuple) else access.allows(target, required))
            if not allowed:
                raise APIError("Permission denied.", 403, headers={"X-Permission-Code": "no_app_access"})
    except NoActiveMembership:
        _handle_denial(mode, request, kwargs, "membership_inactive")
    except APIError as error:
        _handle_denial(mode, request, kwargs, error.headers.get("X-Permission-Code", "action_not_allowed"), error)
    except Exception:
        logger.exception("permission_check_error user=%s route=%s", getattr(request.user, "pk", None), request.path_info)


def _handle_denial(mode, request, kwargs, reason, error=None):
    _log_would_deny(request, _company_id(kwargs), reason)
    if mode == "enforce":
        if error:
            raise error
        raise APIError("Permission denied.", 403, headers={"X-Permission-Code": reason})


def _log_would_deny(request, company_id, reason, hidden_records=0, *, action=None):
    logger.warning("permission_would_deny user=%s company=%s method=%s route=%s action=%s reason=%s hidden_records=%s",
                   getattr(request.user, "pk", None), company_id, request.method, request.path_info,
                   action or "", reason, hidden_records)
