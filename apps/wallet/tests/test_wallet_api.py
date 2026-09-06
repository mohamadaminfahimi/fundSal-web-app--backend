from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import User

pytestmark = pytest.mark.django_db


class TestWalletAPI:
    def test_wallet_endpoint_returns_wallet_for_authenticated_user(self):
        user = User.objects.create_user(
            email="walletapi@example.com",
            password="StrongPass123!",
            first_name="Ali",
            phone_number="+989121234567",
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(reverse("wallet-detail"))

        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["data"]["currency"] == "IRR"

    def test_wallet_requires_authentication(self):
        client = APIClient()
        response = client.get(reverse("wallet-detail"))

        assert response.status_code == 401
