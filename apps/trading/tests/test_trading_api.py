import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import User
from apps.wallet.services import WalletService

pytestmark = pytest.mark.django_db


class TestTradingAPI:
    def test_buy_order_creation_returns_order_for_authenticated_user(self):
        user = User.objects.create_user(
            email="trade@example.com",
            password="StrongPass123!",
            first_name="Ali",
            phone_number="+989121234567",
        )
        WalletService.credit(user, "100000.00", reason="initial-funding")

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            reverse("trading-buy-order"),
            {"metal_code": "XAU", "quantity": "1.0000", "price_per_gram": "1250.50", "idempotency_key": "buy-1"},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["success"] is True
        assert response.data["data"]["side"] == "buy"
        assert response.data["data"]["metal_code"] == "XAU"

    def test_order_list_requires_authentication(self):
        client = APIClient()
        response = client.get(reverse("trading-order-list"))

        assert response.status_code == 401
