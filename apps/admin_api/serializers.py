# apps/admin_api/serializers.py

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.invoices.models import Invoice, InvoiceItem
from apps.trading.models import Order
from apps.wallet.models import AssetHolding, Wallet

User = get_user_model()


# ============================================================
# Auth
# ============================================================

class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


# ============================================================
# User
# ============================================================

class AdminUserListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    wallet_balance = serializers.SerializerMethodField()
    gold_balance = serializers.SerializerMethodField()
    silver_balance = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "phone_number", "is_active", "is_staff", "is_email_verified",
            "date_joined", "wallet_balance", "gold_balance", "silver_balance","is_staff",
        ]
    
    def get_full_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email
    
    def get_wallet_balance(self, obj) -> float:
        try:
            return float(obj.wallet.available_balance)
        except Exception:
            return 0.0
    
    def get_gold_balance(self, obj) -> float:
        try:
            h = obj.asset_holdings.get(metal_code="GOLD")
            return float(h.available_quantity)
        except Exception:
            return 0.0
    
    def get_silver_balance(self, obj) -> float:
        try:
            h = obj.asset_holdings.get(metal_code="SILVER")
            return float(h.available_quantity)
        except Exception:
            return 0.0

class AdminWalletAdjustSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["credit", "debit"])
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    reason = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)  # ✅ اضافه کن



class AdminAssetAdjustSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["credit", "debit"])
    metal_code = serializers.ChoiceField(choices=["GOLD", "SILVER"])
    quantity = serializers.DecimalField(
        max_digits=20, decimal_places=8, min_value=Decimal("0.0001")
    )
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)  # ✅ اضافه کن



# ============================================================
# Invoice
# ============================================================

class AdminInvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ["description", "amount"]


class AdminInvoiceSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    reviewed_by_email = serializers.SerializerMethodField()  # ✅

    class Meta:
        model = Invoice
        fields = [
            "id",
            "number",
            "user",
            "user_email",
            "user_name",
            "transaction_type",
            "total_toman",
            "status",
            "date",
            "created_at",
            "updated_at",
            "items",
            "metadata",
            "admin_note",
            "reviewed_at",
            "reviewed_by",
            "reviewed_by_email",
        ]

    def get_user_name(self, obj):
        name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return name or obj.user.email

    def get_date(self, obj):
        if obj.created_at:
            return obj.created_at.isoformat()
        return None

    def get_reviewed_by_email(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.email
        return None


class AdminInvoiceUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["pending", "paid", "failed"], required=True
    )
    admin_note = serializers.CharField(
        required=False, allow_blank=True, max_length=500
    )


# ============================================================
# Order
# ============================================================

class AdminOrderSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            "id", "user", "user_email", "user_name", "metal_code", "side",
            "order_type", "quantity", "remaining_quantity", "price_per_gram",
            "total_amount", "status", "created_at", "updated_at",
        ]
    
    def get_user_name(self, obj) -> str:
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class AdminOrderUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["pending", "filled", "cancelled", "rejected"], required=True
    )
    admin_note = serializers.CharField(
        required=False, allow_blank=True, max_length=500
    )


# ============================================================
# Market Price
# ============================================================

class AdminPriceSerializer(serializers.Serializer):
    gold_buy_price = serializers.DecimalField(
        max_digits=20, decimal_places=2, required=False
    )
    gold_sell_price = serializers.DecimalField(
        max_digits=20, decimal_places=2, required=False
    )
    silver_buy_price = serializers.DecimalField(
        max_digits=20, decimal_places=2, required=False
    )
    silver_sell_price = serializers.DecimalField(
        max_digits=20, decimal_places=2, required=False
    )
    confidence_range_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        min_value=Decimal("0"), max_value=Decimal("100"),
    )