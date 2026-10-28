from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase

from apps.companies.models import Company
from .models import Invoice, Payment, StockMovement


class DemoWorkspaceTests(TestCase):
    def test_repeatable_demo_preserves_existing_companies_and_password(self):
        user = get_user_model().objects.create_user("demo-owner@example.com", "existing-password-42")
        original_hash = user.password
        original = Company.objects.create(name="Real business", slug="real-business")
        call_command("seed_demo", email=user.email, stdout=StringIO())
        snapshots = (Invoice.objects.count(), Payment.objects.count(), StockMovement.objects.count())
        call_command("seed_demo", email=user.email, stdout=StringIO())
        self.assertEqual((Invoice.objects.count(), Payment.objects.count(), StockMovement.objects.count()), snapshots)
        self.assertTrue(Company.objects.filter(pk=original.pk, name="Real business").exists())
        self.assertFalse(Invoice.objects.filter(company=original).exists())
        user.refresh_from_db()
        self.assertEqual(user.password, original_hash)
        self.assertTrue(Invoice.objects.filter(company__slug=f"kerp-demo-{user.pk}", status="paid").exists())

    def test_demo_requires_existing_active_account(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", email="missing@example.com", stdout=StringIO())
        self.assertFalse(Company.objects.exists())
