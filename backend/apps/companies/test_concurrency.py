from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import Client, TransactionTestCase, skipUnlessDBFeature

from .models import Company, CompanyMembership


class OwnershipConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_simultaneous_owner_demotions_leave_one_active_owner(self):
        company = Company.objects.create(name="Concurrent", slug="concurrent")
        clients = []
        for number in (1, 2):
            user = get_user_model().objects.create_user(f"owner{number}@example.com")
            membership = CompanyMembership.objects.create(company=company, user=user, role="owner")
            client = Client()
            client.force_login(user)
            clients.append((client, membership.pk))
        barrier = Barrier(2)

        def demote(item):
            client, membership_id = item
            try:
                barrier.wait(timeout=10)
                response = client.patch(
                    f"/api/v1/companies/{company.pk}/members/{membership_id}/",
                    {"role": "member"}, content_type="application/json",
                )
                return response.status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(demote, clients))
        self.assertEqual(sorted(statuses), [200, 409])
        self.assertEqual(company.memberships.filter(role="owner", is_active=True).count(), 1)
