from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import TimeStampedModel
from apps.users.models import User


class Order(TimeStampedModel):
    """سفارش خرید/فروش فلزات با اعتبارسنجی‌های مالی و قفل‌سازی مناسب."""

    SIDE_CHOICES = (
        ("buy", "Buy"),
        ("sell", "Sell"),
    )

    ORDER_TYPE_CHOICES = (
        ("limit", "Limit"),
        ("market", "Market"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("partially_filled", "Partially Filled"),
        ("filled", "Filled"),
        ("cancelled", "Cancelled"),
        ("rejected", "Rejected"),
    )

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    metal_code = models.CharField(max_length=20)
    side = models.CharField(max_length=10, choices=SIDE_CHOICES)
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES, default="limit")
    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0.0000"))
    remaining_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0.0000"))
    price_per_gram = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0.0000"))
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    idempotency_key = models.CharField(max_length=128, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "trading_orders"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="order_quantity_positive"),
            models.CheckConstraint(condition=models.Q(remaining_quantity__gte=0), name="order_remaining_quantity_non_negative"),
            models.CheckConstraint(condition=models.Q(price_per_gram__gt=0), name="order_price_positive"),
        ]
        indexes = [
            models.Index(fields=["user", "status", "created_at"]),
            models.Index(fields=["metal_code", "side", "status"]),
            models.Index(fields=["idempotency_key"]),
        ]

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("مقدار سفارش باید بزرگ‌تر از صفر باشد.")
        if self.price_per_gram <= 0:
            raise ValidationError("قیمت هر گرم باید بزرگ‌تر از صفر باشد.")
        if self.remaining_quantity < 0:
            raise ValidationError("مقدار باقیمانده سفارش نمی‌تواند منفی باشد.")

    def __str__(self) -> str:
        return f"{self.user.email}::{self.side}::{self.metal_code}::{self.quantity}"


class OrderExecution(TimeStampedModel):
    """تراکنش‌های تطبیق سفارش‌ها؛ هر اجرا به‌صورت immutable ثبت می‌شود."""

    buy_order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="buy_executions")
    sell_order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="sell_executions")
    executed_quantity = models.DecimalField(max_digits=18, decimal_places=4)
    executed_price = models.DecimalField(max_digits=18, decimal_places=4)
    executed_amount = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        db_table = "trading_order_executions"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Execution({self.executed_quantity} @ {self.executed_price})"
