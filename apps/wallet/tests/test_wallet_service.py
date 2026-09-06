from decimal import Decimal

import pytest

from apps.users.models import User
from apps.wallet.models import Wallet
from apps.wallet.services import WalletService

pytestmark = pytest.mark.django_db


class TestWalletService:
    def test_credit_and_debit_updates_balance(self):
        user = User.objects.create_user(email="wallet@example.com", password="StrongPass123!", first_name="Ali", phone_number="+989121234567")

        WalletService.credit(user, Decimal("1000.00"), reason="initial")
        wallet = Wallet.objects.get(user=user)
        assert wallet.available_balance == Decimal("1000.00")

        WalletService.debit(user, Decimal("250.00"), reason="purchase")
        wallet.refresh_from_db()
        assert wallet.available_balance == Decimal("750.00")
