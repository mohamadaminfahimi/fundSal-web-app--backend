from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import TimeStampedModel
from apps.users.models import User


class Wallet(TimeStampedModel):
    """کیف پول هر کاربر؛ مانده‌ی واقعی پول‌های نقدی به‌صورت Decimal نگه‌داری می‌شود."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    available_balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    pending_balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="IRR")

    class Meta:
        db_table = "wallets"

    def __str__(self) -> str:
        return f"Wallet({self.user.email})"

    @property
    def total_balance(self) -> Decimal:
        return self.available_balance + self.pending_balance

    def clean(self):
        if self.available_balance < 0:
            raise ValidationError("موجودی قابل برداشت نمی‌تواند منفی باشد.")
        if self.pending_balance < 0:
            raise ValidationError("موجودی معلق نمی‌تواند منفی باشد.")


class AssetHolding(TimeStampedModel):
    """موجودی فلزات هر کاربر، برای سفارش‌ها و دارایی‌های فیزیکی/محاسباتی."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assets")
    metal_code = models.CharField(max_length=20)
    available_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0.0000"))
    locked_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0.0000"))

    class Meta:
        db_table = "asset_holdings"
        unique_together = ("user", "metal_code")

    @property
    def total_quantity(self) -> Decimal:
        return self.available_quantity + self.locked_quantity

    def __str__(self) -> str:
        return f"{self.user.email}::{self.metal_code}"
