from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class UserTests(TestCase):
    def test_email_user_has_hashed_password_and_can_authenticate(self):
        user = User.objects.create_user("member@EXAMPLE.COM", "safe-password-42")
        self.assertEqual(user.email, "member@example.com")
        self.assertTrue(user.check_password("safe-password-42"))
        self.assertFalse(user.is_staff)
        self.assertEqual(authenticate(email=user.email, password="safe-password-42"), user)

    def test_email_is_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user("", "safe-password-42")

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user("member@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("member@example.com")

    def test_superuser_requires_staff_and_superuser_flags(self):
        for flags in ({"is_staff": False}, {"is_superuser": False}):
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                User.objects.create_superuser("admin@example.com", **flags)

    def test_admin_login_uses_email(self):
        user = User.objects.create_superuser("admin@example.com", "safe-password-42")
        response = self.client.post(reverse("admin:login"), {
            "username": user.email,
            "password": "safe-password-42",
            "next": reverse("admin:index"),
        })
        self.assertRedirects(response, reverse("admin:index"))
        self.assertContains(self.client.get(reverse("admin:accounts_user_add")), "Email address")
