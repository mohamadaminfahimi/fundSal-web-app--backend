from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.common.utils import quantize_money
from apps.transactions.models import Transaction
from apps.wallet.models import AssetHolding, Wallet


class WalletService:
    """کلاس سرویس کیف پول؛ تمام تغییرات مانده‌ی پول و دارایی‌ها از این سرویس عبور می‌کنند."""

    @staticmethod
    def get_or_create_wallet(user):
        wallet, _ = Wallet.objects.get_or_create(user=user)
        return wallet

    @staticmethod
    def credit(user, amount: Decimal | str, *, reason: str, reference_id: str | None = None, metadata: dict | None = None):
        amount = quantize_money(amount)
        wallet = WalletService.get_or_create_wallet(user)
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
            wallet.available_balance += amount
            wallet.save(update_fields=["available_balance", "updated_at"])
            Transaction.objects.create(
                user=user,
                transaction_type="deposit",
                amount=amount,
                currency=wallet.currency,
                status="completed",
                reference_id=reference_id or f"dep-{user.id}-{wallet.id}",
                metadata={"reason": reason, **(metadata or {})},
            )
        return wallet

    @staticmethod
    def debit(user, amount: Decimal | str, *, reason: str, reference_id: str | None = None, metadata: dict | None = None):
        amount = quantize_money(amount)
        wallet = WalletService.get_or_create_wallet(user)
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
            if wallet.available_balance < amount:
                raise ValueError("INSUFFICIENT_BALANCE")
            wallet.available_balance -= amount
            wallet.save(update_fields=["available_balance", "updated_at"])
            Transaction.objects.create(
                user=user,
                transaction_type="withdrawal",
                amount=amount,
                currency=wallet.currency,
                status="completed",
                reference_id=reference_id or f"wd-{user.id}-{wallet.id}",
                metadata={"reason": reason, **(metadata or {})},
            )
        return wallet

    @staticmethod
    def add_asset(user, metal_code: str, quantity: Decimal | str):
        quantity = Decimal(str(quantity))
        holding, _ = AssetHolding.objects.get_or_create(user=user, metal_code=metal_code)
        with transaction.atomic():
            holding = AssetHolding.objects.select_for_update().get(pk=holding.pk)
            holding.available_quantity += quantity
            holding.save(update_fields=["available_quantity", "updated_at"])
        return holding

    @staticmethod
    def remove_asset(user, metal_code: str, quantity: Decimal | str):
        quantity = Decimal(str(quantity))
        holding = AssetHolding.objects.get(user=user, metal_code=metal_code)
        with transaction.atomic():
            holding = AssetHolding.objects.select_for_update().get(pk=holding.pk)
            if holding.available_quantity < quantity:
                raise ValueError("INSUFFICIENT_ASSET")
            holding.available_quantity -= quantity
            holding.save(update_fields=["available_quantity", "updated_at"])
        return holding
