# apps/invoices/models.py

from __future__ import annotations

import random
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


def generate_invoice_number() -> str:
    """
    ✅ تولید شماره فاکتور یکتا
    
    فرمت: INV-{year}-{random}
    مثال: INV-2026-4821
    """
    prefix = "INV"
    year = timezone.now().year
    
    # حداکثر ۱۰ بار تلاش برای ساخت شماره یکتا
    for _ in range(10):
        random_num = random.randint(1000, 9999)
        number = f"{prefix}-{year}-{random_num}"
        
        # اگه تکراری نبود، برگردون
        if not Invoice.objects.filter(number=number).exists():
            return number
    
    # اگه بعد از ۱۰ بار یکتا نشد، از timestamp استفاده کن
    import time
    return f"{prefix}-{year}-{int(time.time() * 1000) % 1000000}"


class Invoice(TimeStampedModel):
    """
    فاکتور / درخواست واریز یا برداشت
    
    وضعیت‌ها:
    - pending: در انتظار بررسی
    - paid: تایید شده
    - failed: رد شده
    """
    
    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار"
        PAID = "paid", "تایید شده"
        FAILED = "failed", "رد شده"
    
    class TransactionType(models.TextChoices):
        DEPOSIT = "deposit", "واریز"
        WITHDRAW = "withdraw", "برداشت"
        BUY = "buy", "خرید"
        SELL = "sell", "فروش"
    
    # ✅ شماره فاکتور یکتا — خودکار پر میشه
    number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
        default="",
        editable=False,
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoices",
        db_index=True,
    )
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        db_index=True,
    )
    
    total_toman = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    
    # اطلاعات اضافی (شبا، نام صاحب حساب، بانک و ...)
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )
    
    # یادداشت ادمین
    admin_note = models.TextField(
        blank=True,
        default="",
    )
    
    # تاریخ تایید یا رد
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_invoices",
    )
    
    class Meta:
        db_table = "invoices"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["transaction_type"]),
        ]
        verbose_name = "فاکتور"
        verbose_name_plural = "فاکتورها"
    
    def __str__(self):
        return f"{self.number or self.id} - {self.user.email} - {self.total_toman}"
    
    def save(self, *args, **kwargs):
        # ✅ ساخت شماره فاکتور خودکار
        if not self.number:
            self.number = generate_invoice_number()
        
        super().save(*args, **kwargs)
    
    # ============================================================
    # Properties
    # ============================================================
    
    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING
    
    @property
    def is_paid(self) -> bool:
        return self.status == self.Status.PAID
    
    @property
    def is_failed(self) -> bool:
        return self.status == self.Status.FAILED
    
    @property
    def is_deposit(self) -> bool:
        return self.transaction_type == self.TransactionType.DEPOSIT
    
    @property
    def is_withdraw(self) -> bool:
        return self.transaction_type == self.TransactionType.WITHDRAW
    
    # ============================================================
    # Actions
    # ============================================================
    
    def mark_as_paid(self, reviewed_by=None, admin_note: str = ""):
        """تایید فاکتور توسط ادمین"""
        self.status = self.Status.PAID
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewed_by
        if admin_note:
            self.admin_note = admin_note
        self.save()
    
    def mark_as_failed(self, reviewed_by=None, admin_note: str = ""):
        """رد فاکتور توسط ادمین"""
        self.status = self.Status.FAILED
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewed_by
        if admin_note:
            self.admin_note = admin_note
        self.save()


class InvoiceItem(models.Model):
    """آیتم‌های فاکتور"""
    
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
    )
    
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    
    class Meta:
        db_table = "invoice_items"
        ordering = ["id"]
        verbose_name = "آیتم فاکتور"
        verbose_name_plural = "آیتم‌های فاکتور"
    
    def __str__(self):
        return f"{self.invoice.number} - {self.description}"