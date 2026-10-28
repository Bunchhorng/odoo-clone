from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.db import transaction
from django.http import JsonResponse
from django.utils.text import slugify

from apps.accounts.views import session_data
from apps.core.api import APIError, api, json_body, text_field
from .access import company_data, membership_for, memberships_for
from .models import Company, CompanyMembership


def member_data(member):
    return {
        "id": member.pk,
        "user_id": member.user_id,
        "email": member.user.email,
        "name": member.user.get_full_name() or member.user.email,
        "role": member.role,
        "is_active": member.is_active,
        "user_is_active": member.user.is_active,
    }


def manager_for(user, company_id):
    actor = membership_for(user, company_id)
    if actor.role not in (CompanyMembership.Role.OWNER, CompanyMembership.Role.ADMIN):
        raise APIError("Only an owner or administrator can manage team access.", 403)
    return actor


def validate_role(role):
    if not isinstance(role, str) or role not in CompanyMembership.Role.values:
        raise APIError("Choose owner, admin, or member as the role.")


def check_admin_scope(actor, current_role, new_role):
    if actor.role == CompanyMembership.Role.ADMIN and (
        current_role != CompanyMembership.Role.MEMBER or new_role != CompanyMembership.Role.MEMBER
    ):
        raise APIError("Administrators can manage members only. Ask an owner to change privileged access.", 403)


def lock_company(user, company_id):
    # Always lock the parent before reading permissions or changing its team.
    # This serializes owner changes and prevents removing the final owner.
    membership_for(user, company_id)
    if Company.objects.select_for_update().filter(pk=company_id).first() is None:
        raise APIError("Company not found or access is unavailable.", 404)
    return manager_for(user, company_id)


@api(["GET", "POST"])
def companies(request):
    if request.method == "GET":
        return JsonResponse({"companies": [company_data(item) for item in memberships_for(request.user)]})
    data = json_body(request, {"name"})
    name = text_field(data, "name", maximum=200)
    slug = f"{slugify(name)[:40] or 'company'}-{uuid4().hex[:8]}"
    with transaction.atomic():
        company = Company(name=name, slug=slug)
        company.full_clean()
        company.save()
        CompanyMembership.objects.create(company=company, user=request.user, role=CompanyMembership.Role.OWNER)
    request.session["active_company_id"] = company.pk
    return JsonResponse(session_data(request), status=201)


@api(["POST"])
def select_company(request, company_id):
    membership_for(request.user, company_id)
    request.session["active_company_id"] = company_id
    return JsonResponse(session_data(request))


@api(["GET", "POST"])
def members(request, company_id):
    membership_for(request.user, company_id)
    if request.method == "GET":
        team = CompanyMembership.objects.filter(company_id=company_id).select_related("user").order_by("user__email")
        return JsonResponse({"members": [member_data(item) for item in team]})
    with transaction.atomic():
        actor = lock_company(request.user, company_id)
        data = json_body(request, {"email", "role"})
        email = text_field(data, "email", maximum=254)
        validate_email(email)
        role = data.get("role", CompanyMembership.Role.MEMBER)
        validate_role(role)
        check_admin_scope(actor, CompanyMembership.Role.MEMBER, role)
        user = get_user_model().objects.filter(email__iexact=email, is_active=True).first()
        if user is None:
            raise APIError("An active account with this email is required. Ask your Django administrator to create it first.")
        if CompanyMembership.objects.filter(company_id=company_id, user=user).exists():
            raise APIError("This account already belongs to the company. Update its existing access instead.", 409)
        member = CompanyMembership.objects.create(company_id=company_id, user=user, role=role)
        return JsonResponse({"member": member_data(member)}, status=201)


@api(["PATCH"])
def update_member(request, company_id, member_id):
    with transaction.atomic():
        actor = lock_company(request.user, company_id)
        member = CompanyMembership.objects.filter(pk=member_id, company_id=company_id).select_related("user").first()
        if member is None:
            raise APIError("Team member not found.", 404)
        data = json_body(request, {"role", "is_active"})
        if not data:
            raise APIError("Provide a role or active status to update.")
        role = data.get("role", member.role)
        active = data.get("is_active", member.is_active)
        validate_role(role)
        if not isinstance(active, bool):
            raise APIError("Active status must be true or false.")
        check_admin_scope(actor, member.role, role)
        if member.role == CompanyMembership.Role.OWNER and member.is_active and member.user.is_active and (
            role != CompanyMembership.Role.OWNER or not active
        ):
            another_owner = CompanyMembership.objects.filter(
                company_id=company_id, role=CompanyMembership.Role.OWNER,
                is_active=True, user__is_active=True,
            ).exclude(pk=member.pk).exists()
            if not another_owner:
                raise APIError("Keep at least one active owner. Promote another active teammate first.", 409)
        member.role = role
        member.is_active = active
        member.save(update_fields=["role", "is_active"])
        return JsonResponse({"member": member_data(member)})
