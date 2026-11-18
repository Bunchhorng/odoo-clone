from datetime import timedelta
from unittest.mock import patch
from unittest import skipUnless

from django.conf import settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.db import connection

from .models import AuthRateBucket, PasswordResetDelivery
from .recovery import process_next_delivery
from .security import bucket_key

User = get_user_model()


class AuthenticationSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("secure@example.com", "Original-strong-password-42")

    def login(self, email=None, password="wrong", **headers):
        return self.client.post("/api/v1/auth/login/", {
            "email": email or self.user.email, "password": password,
        }, content_type="application/json", **headers)

    @override_settings(AUTH_LOGIN_IDENTITY_LIMIT=2, AUTH_RATE_WINDOW_SECONDS=10)
    def test_login_throttle_counts_case_variants_and_expires(self):
        self.assertEqual(self.login().status_code, 401)
        self.assertEqual(self.login(email="SECURE@EXAMPLE.COM").status_code, 401)
        blocked = self.login(password="Original-strong-password-42")
        self.assertEqual(blocked.status_code, 429)
        self.assertTrue(1 <= int(blocked["Retry-After"]) <= 10)
        self.assertEqual(blocked["Cache-Control"], "private, no-store")
        AuthRateBucket.objects.filter(key=bucket_key("login:identity", self.user.email)).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.login(password="Original-strong-password-42").status_code, 200)
        self.assertFalse(AuthRateBucket.objects.filter(key=bucket_key("login:identity", self.user.email)).exists())

    @override_settings(AUTH_LOGIN_IP_LIMIT=1)
    def test_forwarded_headers_do_not_bypass_ip_limit(self):
        self.assertEqual(self.login(email="missing1@example.com", HTTP_X_FORWARDED_FOR="1.1.1.1").status_code, 401)
        self.assertEqual(self.login(email="missing2@example.com", HTTP_X_FORWARDED_FOR="2.2.2.2").status_code, 429)
        self.assertTrue(all(len(key) == 64 for key in AuthRateBucket.objects.values_list("key", flat=True)))

    def test_login_is_case_insensitive(self):
        self.assertEqual(self.login(email="SECURE@EXAMPLE.COM", password="Original-strong-password-42").status_code, 200)

    @skipUnless(connection.vendor == "mysql", "MySQL collation regression")
    @override_settings(AUTH_LOGIN_IDENTITY_LIMIT=1)
    def test_collation_alias_cannot_bypass_account_throttle(self):
        self.assertTrue(User.objects.filter(email__iexact="secure@\u00e9xample.com").exists())
        self.assertEqual(self.login().status_code, 401)
        self.assertEqual(self.login(email="secure@\u00e9xample.com").status_code, 429)

    def test_password_change_keeps_current_session_and_revokes_other_sessions(self):
        self.client.force_login(self.user)
        other = Client()
        other.force_login(self.user)
        old_session_key = self.client.session.session_key
        response = self.client.post("/api/v1/auth/password/change/", {
            "old_password": "Original-strong-password-42", "new_password1": "Changed-strong-password-91",
            "new_password2": "Changed-strong-password-91",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(self.client.session.session_key, old_session_key)
        self.assertEqual(self.client.get("/api/v1/companies/").status_code, 200)
        self.assertEqual(other.get("/api/v1/companies/").status_code, 401)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Changed-strong-password-91"))

    def test_password_change_rejects_wrong_old_password_and_weak_or_mismatched_values(self):
        self.client.force_login(self.user)
        for old, first, second in (
            ("wrong", "New-strong-password-37", "New-strong-password-37"),
            ("Original-strong-password-42", "12345678", "12345678"),
            ("Original-strong-password-42", "New-strong-password-37", "different"),
        ):
            response = self.client.post("/api/v1/auth/password/change/", {
                "old_password": old, "new_password1": first, "new_password2": second,
            }, content_type="application/json")
            self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Original-strong-password-42"))

    def test_password_endpoints_require_csrf_and_protected_change_requires_login(self):
        strict = Client(enforce_csrf_checks=True)
        for endpoint in ("change", "reset", "reset/confirm"):
            self.assertEqual(strict.post(f"/api/v1/auth/password/{endpoint}/", {}, content_type="application/json").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/auth/password/change/", {}, content_type="application/json").status_code, 401)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordRecoveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("recover@example.com", "Original-strong-password-42")

    def request_reset(self, email):
        return self.client.post("/api/v1/auth/password/reset/", {"email": email}, content_type="application/json")

    def reset(self, token=None, uid=None, password="Recovered-strong-password-64"):
        return self.client.post("/api/v1/auth/password/reset/confirm/", {
            "uid": uid or urlsafe_base64_encode(force_bytes(self.user.pk)),
            "token": token or default_token_generator.make_token(self.user),
            "new_password1": password, "new_password2": password,
        }, content_type="application/json")

    def test_known_and_unknown_accounts_get_same_response_and_queue_behavior(self):
        known = self.request_reset(self.user.email)
        unknown = self.request_reset("unknown@example.com")
        self.assertEqual(known.status_code, 200)
        self.assertEqual(known.json(), unknown.json())
        self.assertEqual(PasswordResetDelivery.objects.count(), 2)
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(process_next_delivery())
        self.assertTrue(process_next_delivery())
        self.assertFalse(process_next_delivery())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(settings.FRONTEND_ORIGIN + "/reset-password#uid=", mail.outbox[0].body)
        self.assertIn("&token=", mail.outbox[0].body)
        self.assertNotIn("Original-strong-password", mail.outbox[0].body)

    @override_settings(AUTH_RESET_IDENTITY_LIMIT=1)
    def test_reset_requests_are_throttled_without_user_lookup(self):
        self.assertEqual(self.request_reset("unknown@example.com").status_code, 200)
        response = self.request_reset("UNKNOWN@EXAMPLE.COM")
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)
        self.assertEqual(PasswordResetDelivery.objects.count(), 1)

    @skipUnless(connection.vendor == "mysql", "MySQL collation regression")
    @override_settings(AUTH_RESET_IDENTITY_LIMIT=1)
    def test_collation_alias_does_not_bypass_recipient_delivery_budget(self):
        self.assertEqual(self.request_reset(self.user.email).status_code, 200)
        self.assertTrue(process_next_delivery())
        self.assertEqual(self.request_reset("recover@\u00e9xample.com").status_code, 200)
        self.assertTrue(process_next_delivery())
        self.assertEqual(len(mail.outbox), 1)

    def test_reset_invalidates_other_sessions_and_cannot_be_reused(self):
        other = Client()
        other.force_login(self.user)
        token = default_token_generator.make_token(self.user)
        self.assertEqual(self.reset(token).status_code, 200)
        self.assertEqual(other.get("/api/v1/companies/").status_code, 401)
        self.assertEqual(self.reset(token).status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Recovered-strong-password-64"))

    def test_weak_reset_password_keeps_token_usable(self):
        token = default_token_generator.make_token(self.user)
        self.assertEqual(self.reset(token, password="12345678").status_code, 400)
        self.assertEqual(self.reset(token).status_code, 200)

    def test_expired_invalid_and_foreign_tokens_are_rejected(self):
        token = default_token_generator.make_token(self.user)
        later = default_token_generator._now() + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT + 5)
        with patch.object(default_token_generator, "_now", return_value=later):
            self.assertEqual(self.reset(token).status_code, 400)
        self.assertEqual(self.reset(token="invalid").status_code, 400)
        self.assertEqual(self.reset(token, uid="not-a-user").status_code, 400)
        self.assertEqual(self.reset(token, uid=urlsafe_base64_encode(b"9999999999999999999999999999999")).status_code, 400)
        other = User.objects.create_user("other@example.com", "Other-strong-password-94")
        self.assertEqual(self.reset(default_token_generator.make_token(other)).status_code, 400)

    def test_inactive_or_unusable_accounts_do_not_receive_mail(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.request_reset(self.user.email).status_code, 200)
        self.assertTrue(process_next_delivery())
        unusable = User.objects.create_user("unusable@example.com")
        self.assertEqual(self.request_reset(unusable.email).status_code, 200)
        self.assertTrue(process_next_delivery())
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(self.reset().status_code, 400)

    def test_mail_failure_retries_without_logging_recipient_or_secrets(self):
        self.request_reset(self.user.email)
        for attempt in range(1, 4):
            with patch("apps.accounts.recovery.EmailMultiAlternatives.send", side_effect=OSError("private SMTP secret")):
                with self.assertLogs("apps.accounts.recovery", level="WARNING") as logs:
                    self.assertTrue(process_next_delivery())
            self.assertNotIn("private SMTP secret", " ".join(logs.output))
            self.assertNotIn(self.user.email, " ".join(logs.output))
            job = PasswordResetDelivery.objects.get()
            self.assertEqual(job.attempts, attempt)
            if attempt < 3:
                self.assertEqual(job.status, "pending")
                self.assertFalse(process_next_delivery())
                job.next_attempt_at = timezone.now() - timedelta(seconds=1)
                job.save()
        self.assertEqual(job.status, "failed")
        self.assertIsNotNone(job.processed_at)

    def test_expired_queued_request_does_not_send_mail(self):
        PasswordResetDelivery.objects.create(email=self.user.email,
            created_at=timezone.now() - timedelta(seconds=settings.AUTH_RESET_QUEUE_TTL + 1))
        self.assertTrue(process_next_delivery())
        self.assertEqual(PasswordResetDelivery.objects.get().status, "failed")
        self.assertEqual(len(mail.outbox), 0)
