from .models import CompanyMembership
from apps.core.api import APIError


def memberships_for(user):
    return CompanyMembership.objects.filter(
        user=user, is_active=True, company__is_active=True,
    ).select_related("company").order_by("company__name", "company_id")


def membership_for(user, company_id):
    membership = memberships_for(user).filter(company_id=company_id).first()
    if membership is None:
        # Do not reveal whether another company's ID exists.
        raise APIError("Company not found or access is unavailable.", 404)
    return membership


def company_data(membership):
    return {
        "id": membership.company_id,
        "name": membership.company.name,
        "slug": membership.company.slug,
        "role": membership.role,
    }
