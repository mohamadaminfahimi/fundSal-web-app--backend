from __future__ import annotations

from decimal import Decimal

from django.db import models

from apps.common.models import TimeStampedModel
from apps.users.models import User


class PreciousMetal(models.Model):
    """نوع فلز پایه‌ای که برای بازار، سفارش‌ها و موجودی‌ها استفاده می‌شود."""

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)
    unit = models.CharField(max_length=20, default="gram")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "market_metals"
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class MarketPrice(TimeStampedModel):
    """قیمت لحظه‌ای بازار برای هر فلز."""

    metal = models.ForeignKey(PreciousMetal, on_delete=models.CASCADE, related_name="prices")
    price_per_gram = models.DecimalField(max_digits=18, decimal_places=4)
    source = models.CharField(max_length=80, default="internal_provider")
    valid_from = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "market_prices"
        indexes = [models.Index(fields=["metal", "valid_from"])]

    def __str__(self) -> str:
        return f"{self.metal.code} @ {self.price_per_gram}"


class PriceHistory(TimeStampedModel):
    """تاریخچه‌ی قیمت‌ها برای تحلیل، نمودار و نمایش قیمت‌های گذشته."""

    metal = models.ForeignKey(PreciousMetal, on_delete=models.CASCADE, related_name="history")
    price_per_gram = models.DecimalField(max_digits=18, decimal_places=4)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "market_price_history"
        indexes = [models.Index(fields=["metal", "recorded_at"])]

    def __str__(self) -> str:
        return f"{self.metal.code} / {self.price_per_gram}"
