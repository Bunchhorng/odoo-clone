from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.companies.models import Company, CompanyMembership

User = get_user_model()


class AuthenticationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("user@example.com", "correct-horse-battery-42")
        cls.company = Company.objects.create(name="Example", slug="example")
        CompanyMembership.objects.create(company=cls.company, user=cls.user, role="owner")

    def test_anonymous_session_sets_csrf_cookie_and_hides_data(self):
        response = self.client.get("/api/v1/auth/session/")
        self.assertEqual(response.json(), {"user": None, "companies": [], "active_company_id": None})
        self.assertIn("csrftoken", response.cookies)
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_login_session_and_logout(self):
        response = self.client.post("/api/v1/auth/login/", {
            "email": " user@example.com ", "password": "correct-horse-battery-42",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], self.user.email)
        self.assertNotIn("password", response.content.decode())
        self.assertEqual(response.json()["active_company_id"], self.company.pk)
        self.assertEqual(self.client.get("/api/v1/auth/session/").json()["user"]["id"], self.user.pk)
        self.assertIsNone(self.client.post("/api/v1/auth/logout/").json()["user"])
        self.assertEqual(self.client.get("/api/v1/companies/").status_code, 401)

    def test_bad_password_and_inactive_account_are_rejected(self):
        for password, active in (("incorrect", True), ("correct-horse-battery-42", False)):
            self.user.is_active = active
            self.user.save()
            response = self.client.post("/api/v1/auth/login/", {
                "email": self.user.email, "password": password,
            }, content_type="application/json")
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["error"], "Email or password is incorrect.")

    def test_invalid_login_payloads_are_json_errors(self):
        for payload in ("{", "[]", '{"email":123}', '{"password":[]}', '{"extra":true}'):
            response = self.client.post("/api/v1/auth/login/", payload, content_type="application/json")
            self.assertEqual(response.status_code, 400)
            self.assertIn("error", response.json())
        self.assertEqual(self.client.post("/api/v1/auth/login/", {}).status_code, 415)
        self.assertEqual(self.client.get("/api/v1/auth/login/").status_code, 405)

    def test_csrf_is_required_for_login_and_authenticated_writes(self):
        client = Client(enforce_csrf_checks=True)
        payload = {"email": self.user.email, "password": "correct-horse-battery-42"}
        self.assertEqual(client.post("/api/v1/auth/login/", payload, content_type="application/json").status_code, 403)
        client.get("/api/v1/auth/session/")
        old_token = client.cookies["csrftoken"].value
        response = client.post("/api/v1/auth/login/", payload, content_type="application/json", HTTP_X_CSRFTOKEN=old_token)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(old_token, client.cookies["csrftoken"].value)
        self.assertEqual(client.post("/api/v1/auth/logout/").status_code, 403)
        self.assertEqual(client.post("/api/v1/auth/logout/", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value).status_code, 200)

    def test_removed_membership_clears_active_company(self):
        self.client.force_login(self.user)
        self.client.get("/api/v1/auth/session/")
        CompanyMembership.objects.filter(user=self.user).update(is_active=False)
        response = self.client.get("/api/v1/auth/session/").json()
        self.assertEqual(response["companies"], [])
        self.assertIsNone(response["active_company_id"])

    def test_disabling_account_revokes_existing_session(self):
        self.client.force_login(self.user)
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.client.get("/api/v1/companies/").status_code, 401)
        self.assertIsNone(self.client.get("/api/v1/auth/session/").json()["user"])

    def test_csrf_rejects_untrusted_origin_even_with_valid_token(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/api/v1/auth/session/")
        response = client.post("/api/v1/auth/login/", {
            "email": self.user.email, "password": "correct-horse-battery-42",
        }, content_type="application/json", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
            HTTP_ORIGIN="https://untrusted.example")
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.json())
