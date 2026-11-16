from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import (
    AppAccessRight, AppRecordRule, Company, CompanyAccessGroup,
    CompanyAccessGroupMembership, CompanyMembership, UserAppAccessOverride,
)
from .permissions import NoActiveMembership, resolve_effective_access


User = get_user_model()


class PermissionResolutionTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Access Co", slug="access-co")
        self.user = User.objects.create_user("member@example.test")
        self.owner = User.objects.create_user("owner@example.test")
        CompanyMembership.objects.create(company=self.company, user=self.user, role="member")
        CompanyMembership.objects.create(company=self.company, user=self.owner, role="owner")
        self.sales = self.group("sales")
        self.crm = self.group("crm")

    def group(self, code):
        group = CompanyAccessGroup.objects.create(company=self.company, name=code.title(), code=code)
        CompanyAccessGroupMembership.objects.create(group=group, user=self.user)
        return group

    def grant(self, group, app, **actions):
        return AppAccessRight.objects.create(company=self.company, group=group, app_key=app, **{
            f"can_{action}": value for action, value in actions.items()
        })

    def test_default_is_deny_and_active_membership_is_required(self):
        access = resolve_effective_access(self.user, self.company.pk)
        self.assertFalse(access.allows("sales", "read"))
        outsider = User.objects.create_user("outsider@example.test")
        with self.assertRaises(NoActiveMembership):
            resolve_effective_access(outsider, self.company.pk)

    def test_inactive_membership_has_no_access(self):
        CompanyMembership.objects.filter(company=self.company, user=self.user).update(is_active=False)
        with self.assertRaises(NoActiveMembership):
            resolve_effective_access(self.user, self.company.pk)

    def test_group_rights_are_additive(self):
        self.grant(self.sales, "sales", read=True, create=True)
        self.grant(self.crm, "sales", write=True, approve=True)
        access = resolve_effective_access(self.user, self.company.pk)
        self.assertEqual(access.permissions["sales"], {"read", "create", "write", "approve"})
        self.assertFalse(access.allows("sales", "delete"))

    def test_explicit_revoke_wins_over_group_grant(self):
        self.grant(self.sales, "sales", read=True, write=True)
        UserAppAccessOverride.objects.create(company=self.company, user=self.user, app_key="sales", can_read=False, can_write=True)
        access = resolve_effective_access(self.user, self.company.pk)
        self.assertFalse(access.allows("sales", "read"))
        self.assertTrue(access.allows("sales", "write"))

    def test_user_grant_override_works_without_a_group(self):
        user = User.objects.create_user("override@example.test")
        CompanyMembership.objects.create(company=self.company, user=user, role="member")
        UserAppAccessOverride.objects.create(
            company=self.company, user=user, app_key="helpdesk", can_read=True,
        )
        self.assertTrue(resolve_effective_access(user, self.company.pk).allows("helpdesk", "read"))

    def test_inactive_group_rights_are_ignored(self):
        self.grant(self.sales, "sales", read=True)
        self.sales.is_active = False
        self.sales.save(update_fields=["is_active"])
        self.assertFalse(resolve_effective_access(self.user, self.company.pk).allows("sales", "read"))

    def test_implied_contact_and_product_reads_are_read_only(self):
        self.grant(self.sales, "sales", read=True)
        access = resolve_effective_access(self.user, self.company.pk)
        for app in ("contacts", "products", "product-categories"):
            self.assertTrue(access.allows(app, "read"))
            for action in ("create", "write", "delete", "approve"):
                self.assertFalse(access.allows(app, action))
            self.assertEqual(access.scopes_for(app, "*"), {AppRecordRule.Scope.ALL_COMPANY})
        UserAppAccessOverride.objects.create(company=self.company, user=self.user, app_key="contacts", can_read=False)
        self.assertFalse(resolve_effective_access(self.user, self.company.pk).allows("contacts", "read"))

    def test_write_never_implies_approve(self):
        self.grant(self.sales, "sales", write=True)
        access = resolve_effective_access(self.user, self.company.pk)
        self.assertTrue(access.allows("sales", "write"))
        self.assertFalse(access.allows("sales", "approve"))

    def test_record_scopes_are_additive(self):
        self.grant(self.sales, "sales", read=True)
        AppRecordRule.objects.create(company=self.company, group=self.sales, app_key="sales", model_key="business.order", scope="own")
        AppRecordRule.objects.create(company=self.company, group=self.crm, app_key="sales", model_key="business.order", scope="assigned")
        access = resolve_effective_access(self.user, self.company.pk)
        self.assertEqual(access.scopes_for("sales", "business.order"), {"own", "assigned"})

    def test_owner_always_has_every_action_and_company_scope(self):
        access = resolve_effective_access(self.owner, self.company.pk)
        for action in ("read", "create", "write", "delete", "approve"):
            self.assertTrue(access.allows("inventory", action))
        self.assertEqual(access.scopes_for("inventory", "business.stockmovement"), {AppRecordRule.Scope.ALL_COMPANY})

    def test_owner_bypass_applies_only_to_own_active_company(self):
        other_company = Company.objects.create(name="Other Co", slug="other-co")
        CompanyMembership.objects.create(company=other_company, user=self.owner, role="owner", is_active=False)
        with self.assertRaises(NoActiveMembership):
            resolve_effective_access(self.owner, other_company.pk)

    def test_cross_company_rights_do_not_grant_access(self):
        self.grant(self.sales, "sales", read=True)
        other_company = Company.objects.create(name="Other Co", slug="other-co")
        CompanyMembership.objects.create(company=other_company, user=self.user, role="member")
        self.assertFalse(resolve_effective_access(self.user, other_company.pk).allows("sales", "read"))

    def test_unsupported_record_rule_scope_is_rejected(self):
        rule = AppRecordRule(
            company=self.company,
            group=self.sales,
            app_key="contacts",
            model_key="business.contact",
            scope=AppRecordRule.Scope.OWN,
        )
        with self.assertRaises(ValidationError) as error:
            rule.full_clean()
        self.assertIn("own is not supported for business.contact", str(error.exception))
