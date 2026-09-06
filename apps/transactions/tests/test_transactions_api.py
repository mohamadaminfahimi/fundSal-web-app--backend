import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.transactions.models import Transaction
from apps.users.models import User

pytestmark = pytest.mark.django_db


class TestTransactionAPI:
    def test_transaction_list_returns_only_authenticated_user_transactions(self):
        user = User.objects.create_user(
            email="txn@example.com",
            password="StrongPass123!",
            first_name="Ali",
            phone_number="+989121234567",
        )
        other = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            first_name="Sara",
            phone_number="+989121234568",
        )

        Transaction.objects.create(
            user=user,
            transaction_type="deposit",
            amount="1500.00",
            currency="IRR",
            status="completed",
            reference_id="dep-1",
        )
        Transaction.objects.create(
            user=other,
            transaction_type="withdrawal",
            amount="50.00",
            currency="IRR",
            status="completed",
            reference_id="wd-1",
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(reverse("transaction-list"))

        assert response.status_code == 200
        assert response.data["success"] is True
        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["reference_id"] == "dep-1"

    def test_transaction_list_requires_authentication(self):
        client = APIClient()
        response = client.get(reverse("transaction-list"))

        assert response.status_code == 401
