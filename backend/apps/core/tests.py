from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse


class HealthTests(TestCase):
    def test_health_checks_real_database(self):
        response = self.client.get(reverse("core:health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "connected"})

    def test_database_failure_returns_503_without_exposing_details(self):
        with patch("apps.core.views.connection.cursor", side_effect=OperationalError("private database details")):
            with self.assertLogs("apps.core.views", level="ERROR"):
                response = self.client.get(reverse("core:health"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "error", "database": "disconnected"})
        self.assertNotContains(response, "private database details", status_code=503)

    def test_health_rejects_post(self):
        self.assertEqual(self.client.post(reverse("core:health")).status_code, 405)
