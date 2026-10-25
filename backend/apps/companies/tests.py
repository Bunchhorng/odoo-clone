from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Company, CompanyMembership


class CompanyTests(TestCase):
    def test_user_can_belong_to_multiple_companies(self):
        user = get_user_model().objects.create_user("member@example.com")
        for slug in ("first", "second"):
            company = Company.objects.create(name=slug.title(), slug=slug)
            CompanyMembership.objects.create(company=company, user=user)
        self.assertEqual(user.company_memberships.count(), 2)

    def test_duplicate_membership_is_rejected(self):
        user = get_user_model().objects.create_user("member@example.com")
        company = Company.objects.create(name="Example", slug="example")
        CompanyMembership.objects.create(company=company, user=user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CompanyMembership.objects.create(company=company, user=user)
