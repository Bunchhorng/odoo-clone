from importlib import import_module

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.api import APIError
from .access import owner_only_for
from .models import (
    AppAccessRight, Company, CompanyAccessGroup, CompanyAccessGroupMembership,
    CompanyMembership,
)
from .seeding import seed_company, sync_membership_system_groups


User = get_user_model()


class SystemAccessSeedTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Seed Co", slug="seed-co")
        self.owner = User.objects.create_user("owner@seed.test")
        self.admin = User.objects.create_user("admin@seed.test")
        self.member = User.objects.create_user("member@seed.test")
        self.owner_membership = CompanyMembership.objects.create(company=self.company, user=self.owner, role="owner")
        self.admin_membership = CompanyMembership.objects.create(company=self.company, user=self.admin, role="admin")
        self.member_membership = CompanyMembership.objects.create(company=self.company, user=self.member, role="member")

    def system_group(self, key):
        return CompanyAccessGroup.objects.get(company=self.company, system_key=key)

    def test_seed_twice_is_create_missing_only_and_idempotent(self):
        seed_company(self.company)
        before = (CompanyAccessGroup.objects.count(), AppAccessRight.objects.count())
        seed_company(self.company)
        self.assertEqual(before, (CompanyAccessGroup.objects.count(), AppAccessRight.objects.count()))

    def test_seed_does_not_overwrite_a_customized_system_right(self):
        seed_company(self.company)
        right = AppAccessRight.objects.get(group=self.system_group("member"), app_key="contacts")
        right.can_read = False
        right.can_write = True
        right.save(update_fields=["can_read", "can_write"])
        seed_company(self.company)
        right.refresh_from_db()
        self.assertFalse(right.can_read)
        self.assertTrue(right.can_write)

    def test_new_company_seed_contains_admin_and_member_groups_and_rights(self):
        groups = seed_company(self.company)
        self.assertEqual(set(groups), {"admin", "member"})
        self.assertTrue(groups["admin"].is_system)
        self.assertTrue(AppAccessRight.objects.filter(group=groups["admin"], app_key="sales", can_approve=True).exists())
        self.assertTrue(AppAccessRight.objects.filter(group=groups["member"], app_key="timesheets", can_create=True).exists())

    def test_existing_companies_are_backfilled_by_migration_function(self):
        migration = import_module("apps.companies.migrations.0006_seed_system_access_groups")
        from django.apps import apps as django_apps
        migration.seed_existing_companies(django_apps, None)
        self.assertTrue(CompanyAccessGroup.objects.filter(company=self.company, system_key="admin").exists())
        self.assertTrue(CompanyAccessGroupMembership.objects.filter(group__system_key="admin", user=self.admin).exists())
        self.assertTrue(CompanyAccessGroupMembership.objects.filter(group__system_key="member", user=self.member).exists())
        self.assertFalse(CompanyAccessGroupMembership.objects.filter(group__is_system=True, user=self.owner).exists())

    def test_role_change_member_to_admin_and_back_updates_only_system_groups(self):
        seed_company(self.company)
        custom = CompanyAccessGroup.objects.create(company=self.company, name="Custom", code="custom")
        CompanyAccessGroupMembership.objects.create(group=custom, user=self.member)
        self.member_membership.role = "admin"
        self.member_membership.save(update_fields=["role"])
        sync_membership_system_groups(self.member_membership)
        self.assertTrue(CompanyAccessGroupMembership.objects.filter(group=self.system_group("admin"), user=self.member).exists())
        self.assertFalse(CompanyAccessGroupMembership.objects.filter(group=self.system_group("member"), user=self.member).exists())
        self.assertTrue(CompanyAccessGroupMembership.objects.filter(group=custom, user=self.member).exists())
        self.member_membership.role = "member"
        self.member_membership.save(update_fields=["role"])
        sync_membership_system_groups(self.member_membership)
        self.assertTrue(CompanyAccessGroupMembership.objects.filter(group=self.system_group("member"), user=self.member).exists())
        self.assertTrue(CompanyAccessGroupMembership.objects.filter(group=custom, user=self.member).exists())

    def test_owner_only_flag_rejects_admin_even_with_settings_write(self):
        seed_company(self.company)
        admin_group = self.system_group("admin")
        self.assertTrue(AppAccessRight.objects.filter(group=admin_group, app_key="settings", can_write=True).exists())
        with self.assertRaises(APIError) as error:
            owner_only_for(self.admin, self.company.pk)
        self.assertEqual(error.exception.status, 403)
        self.assertEqual(owner_only_for(self.owner, self.company.pk).pk, self.owner_membership.pk)

    def test_seeding_one_company_never_touches_another(self):
        other = Company.objects.create(name="Other", slug="other")
        seed_company(self.company)
        self.assertFalse(CompanyAccessGroup.objects.filter(company=other).exists())
