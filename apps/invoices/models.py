from __future__ import annotations

from decimal import Decimal

from django.db import models

from apps.common.models import TimeStampedModel
from apps.users.models import User


class Invoice(TimeStampedModel):
    """فاکتورهای نهایی برای سفارش‌های خرید/فروش که به کاربر ارائه می‌شود."""

    INVOICE_STATUSES = (
        ("draft", "Draft"),
        ("issued", "Issued"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="invoices")
    invoice_number = models.CharField(max_length=40, unique=True)
    order_type = models.CharField(max_length=12, choices=[("buy", "Buy"), ("sell", "Sell")])
    metal_code = models.CharField(max_length=20)
    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0.0000"))
    unit_price = models.DecimalField(max_digits=18, decimal_places=4)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, choices=INVOICE_STATUSES, default="draft")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "invoices"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.invoice_number} - {self.user.email}"
