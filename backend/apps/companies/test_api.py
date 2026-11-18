from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Company, CompanyMembership

User = get_user_model()


class CompanyAccessAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner@example.com")
        cls.admin = User.objects.create_user("admin@example.com")
        cls.member = User.objects.create_user("member@example.com")
        cls.other = User.objects.create_user("other@example.com")
        cls.company = Company.objects.create(name="First", slug="first")
        cls.private = Company.objects.create(name="Private", slug="private")
        cls.owner_access = CompanyMembership.objects.create(company=cls.company, user=cls.owner, role="owner")
        cls.admin_access = CompanyMembership.objects.create(company=cls.company, user=cls.admin, role="admin")
        cls.member_access = CompanyMembership.objects.create(company=cls.company, user=cls.member)
        cls.other_access = CompanyMembership.objects.create(company=cls.private, user=cls.other, role="owner")

    def setUp(self):
        self.client.force_login(self.owner)

    def team_url(self, company=None, member=None):
        base = f"/api/v1/companies/{(company or self.company).pk}/members/"
        return f"{base}{member.pk}/" if member else base

    def add(self, email="other@example.com", role="member"):
        return self.client.post(self.team_url(), {"email": email, "role": role}, content_type="application/json")

    def update(self, member, data, company=None):
        return self.client.patch(self.team_url(company, member), data, content_type="application/json")

    def test_anonymous_cannot_read_or_create_companies(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/v1/companies/").status_code, 401)
        self.assertEqual(self.client.post("/api/v1/companies/", {"name": "No"}, content_type="application/json").status_code, 401)

    def test_only_active_companies_and_memberships_are_listed(self):
        self.assertEqual([item["id"] for item in self.client.get("/api/v1/companies/").json()["companies"]], [self.company.pk])
        self.company.is_active = False
        self.company.save()
        self.assertEqual(self.client.get("/api/v1/companies/").json()["companies"], [])
        self.assertEqual(self.client.get(self.team_url()).status_code, 404)

    def test_create_company_creates_owner_and_selects_it(self):
        response = self.client.post("/api/v1/companies/", {"name": " New Company "}, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        company_id = response.json()["active_company_id"]
        company = Company.objects.get(pk=company_id)
        self.assertEqual(company.name, "New Company")
        self.assertEqual(company.memberships.get(user=self.owner).role, "owner")
        self.assertEqual(self.client.get("/api/v1/auth/session/").json()["active_company_id"], company_id)

    def test_company_name_validation(self):
        for name in ("", " ", "x" * 201, 12):
            response = self.client.post("/api/v1/companies/", {"name": name}, content_type="application/json")
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Company.objects.count(), 2)

    def test_switch_company_persists_and_rejects_unrelated_company(self):
        CompanyMembership.objects.create(company=self.private, user=self.owner)
        url = f"/api/v1/companies/{self.private.pk}/select/"
        self.assertEqual(self.client.post(url).json()["active_company_id"], self.private.pk)
        self.assertEqual(self.client.get("/api/v1/auth/session/").json()["active_company_id"], self.private.pk)
        CompanyMembership.objects.filter(company=self.private, user=self.owner).update(is_active=False)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/auth/session/").json()["active_company_id"], self.company.pk)

    def test_cross_company_reads_and_writes_are_rejected(self):
        self.assertEqual(self.client.get(self.team_url(self.private)).status_code, 404)
        self.assertEqual(self.update(self.other_access, {"role": "member"}, self.private).status_code, 404)
        self.assertEqual(self.update(self.other_access, {"role": "member"}).status_code, 404)
        self.other_access.refresh_from_db()
        self.assertEqual(self.other_access.role, "owner")

    def test_owner_can_add_and_change_roles_and_reactivate(self):
        response = self.add(role="admin")
        self.assertEqual(response.status_code, 201)
        access = CompanyMembership.objects.get(pk=response.json()["member"]["id"])
        self.assertEqual(self.update(access, {"role": "owner"}).status_code, 200)
        self.assertEqual(self.update(access, {"is_active": False}).status_code, 200)
        self.assertEqual(self.update(access, {"is_active": True, "role": "member"}).status_code, 200)

    def test_duplicate_missing_and_inactive_accounts(self):
        self.assertEqual(self.add(email=self.member.email).status_code, 409)
        self.assertEqual(self.add(email="missing@example.com").status_code, 400)
        self.other.is_active = False
        self.other.save()
        self.assertEqual(self.add().status_code, 400)

    def test_member_can_read_team_but_cannot_manage_it(self):
        self.client.force_login(self.member)
        self.assertEqual(len(self.client.get(self.team_url()).json()["members"]), 3)
        self.assertEqual(self.add().status_code, 403)
        self.assertEqual(self.update(self.member_access, {"role": "owner"}).status_code, 403)

    def test_admin_can_manage_members_but_cannot_change_privileged_roles(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.add().status_code, 201)
        self.assertEqual(self.update(self.member_access, {"is_active": False}).status_code, 200)
        self.assertEqual(self.update(self.member_access, {"is_active": True}).status_code, 200)
        for target, data in (
            (self.member_access, {"role": "admin"}),
            (self.admin_access, {"is_active": False}),
            (self.owner_access, {"role": "member"}),
        ):
            self.assertEqual(self.update(target, data).status_code, 403)
        self.assertEqual(self.add(email="someone@example.com", role="owner").status_code, 403)

    def test_final_owner_cannot_be_demoted_or_deactivated(self):
        for data in ({"role": "member"}, {"is_active": False}):
            self.assertEqual(self.update(self.owner_access, data).status_code, 409)
        self.assertEqual(self.update(self.member_access, {"role": "owner"}).status_code, 200)
        self.assertEqual(self.update(self.owner_access, {"role": "member"}).status_code, 200)
        self.assertEqual(self.update(self.member_access, {"is_active": False}).status_code, 403)

    def test_inactive_owner_does_not_allow_removing_final_active_owner(self):
        self.member_access.role = "owner"
        self.member_access.is_active = False
        self.member_access.save()
        self.assertEqual(self.update(self.owner_access, {"is_active": False}).status_code, 409)
        self.member_access.is_active = True
        self.member_access.save()
        self.member.is_active = False
        self.member.save()
        self.assertEqual(self.update(self.owner_access, {"role": "admin"}).status_code, 409)

    def test_invalid_updates_are_rejected_without_changes(self):
        for data in ({}, {"role": "root"}, {"role": []}, {"is_active": "false"}, {"company_id": self.private.pk}):
            self.assertEqual(self.update(self.member_access, data).status_code, 400)
        self.member_access.refresh_from_db()
        self.assertTrue(self.member_access.is_active)
        self.assertEqual(self.member_access.role, "member")

    def test_staff_has_no_implicit_company_access(self):
        superuser = User.objects.create_superuser("root@example.com")
        self.client.force_login(superuser)
        self.assertEqual(self.client.get("/api/v1/companies/").json()["companies"], [])
        self.assertEqual(self.client.get(self.team_url()).status_code, 404)

    def test_deactivated_membership_takes_effect_on_next_request(self):
        self.client.force_login(self.member)
        self.member_access.is_active = False
        self.member_access.save()
        self.assertEqual(self.client.get(self.team_url()).status_code, 404)
