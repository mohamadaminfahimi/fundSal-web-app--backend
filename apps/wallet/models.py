# apps/wallet/models.py

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F

from apps.common.models import TimeStampedModel


class Wallet(TimeStampedModel):
    """کیف پول کاربر"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
        db_index=True,
    )

    available_balance = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("0.00")
    )
    pending_balance = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("0.00")
    )
    # ✅ اگه این فیلد رو نداری، اضافه کن
    total_balance = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("0.00")
    )
    currency = models.CharField(max_length=10, default="IRR")

    class Meta:
        db_table = "wallets"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["-updated_at"]),
        ]

    def __str__(self):
        return f"Wallet({self.user_id}): {self.available_balance}"

    def save(self, *args, **kwargs):
        # ✅ محاسبه خودکار total_balance
        self.total_balance = self.available_balance + self.pending_balance
        super().save(*args, **kwargs)


class AssetHolding(TimeStampedModel):
    """دارایی فلزی کاربر"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asset_holdings",
        db_index=True,
    )
    metal_code = models.CharField(max_length=20, db_index=True)
    available_quantity = models.DecimalField(
        max_digits=20, decimal_places=8, default=Decimal("0.00000000")
    )
    locked_quantity = models.DecimalField(
        max_digits=20, decimal_places=8, default=Decimal("0.00000000")
    )

    class Meta:
        db_table = "asset_holdings"
        unique_together = [["user", "metal_code"]]
        indexes = [
            models.Index(fields=["user", "metal_code"]),
            models.Index(fields=["user", "available_quantity"]),
        ]

    @property
    def total_quantity(self):
        return self.available_quantity + self.locked_quantity

    def __str__(self):
        return f"{self.user_id} - {self.metal_code}: {self.available_quantity}"