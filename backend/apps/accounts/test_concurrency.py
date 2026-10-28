from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db import connections
from django.test import Client, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


class AuthenticationConcurrencyTests(TransactionTestCase):
    def run_parallel(self, endpoint, bodies):
        barrier = Barrier(2)

        def run(index):
            try:
                barrier.wait(timeout=10)
                return Client().post(endpoint, bodies[index], content_type="application/json").status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return sorted(pool.map(run, (0, 1)))

    @skipUnlessDBFeature("has_select_for_update")
    @override_settings(AUTH_LOGIN_IDENTITY_LIMIT=1)
    def test_shared_throttle_does_not_admit_two_concurrent_attempts(self):
        user = get_user_model().objects.create_user("limited@example.com", "Original-strong-password-42")
        body = {"email": user.email, "password": "wrong"}
        self.assertEqual(self.run_parallel("/api/v1/auth/login/", [body, body]), [401, 429])

    @skipUnlessDBFeature("has_select_for_update")
    def test_one_reset_token_cannot_be_consumed_twice_concurrently(self):
        user = get_user_model().objects.create_user("reset-parallel@example.com", "Original-strong-password-42")
        payload = {"uid": urlsafe_base64_encode(force_bytes(user.pk)), "token": default_token_generator.make_token(user)}
        bodies = [{**payload, "new_password1": password, "new_password2": password}
                  for password in ("First-new-strong-password-76", "Second-new-strong-password-81")]
        self.assertEqual(self.run_parallel("/api/v1/auth/password/reset/confirm/", bodies), [200, 400])
