from __future__ import annotations

from decimal import Decimal

from django.db import models

from apps.common.models import TimeStampedModel
from apps.users.models import User


class Transaction(TimeStampedModel):
    """تمام تراکنش‌های مالی به‌صورت یک‌جا و immutable ثبت می‌شوند."""

    TRANSACTION_TYPES = (
        ("deposit", "Deposit"),
        ("withdrawal", "Withdrawal"),
        ("buy_order", "Buy Order"),
        ("sell_order", "Sell Order"),
        ("fee", "Fee"),
        ("adjustment", "Adjustment"),
    )

    STATUSES = (
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("reversed", "Reversed"),
    )

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="IRR")
    status = models.CharField(max_length=20, choices=STATUSES, default="pending")
    reference_id = models.CharField(max_length=100, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "transactions"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.user.email}::{self.transaction_type}::{self.amount}"
