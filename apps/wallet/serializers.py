from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from .models import AssetHolding, Wallet


class WalletSerializer(serializers.ModelSerializer):
    total_balance = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = Wallet
        fields = ["id", "user", "available_balance", "pending_balance", "total_balance", "currency", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "available_balance", "pending_balance", "total_balance", "currency", "created_at", "updated_at"]


class AssetHoldingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetHolding
        fields = ["id", "user", "metal_code", "available_quantity", "locked_quantity", "total_quantity", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "metal_code", "available_quantity", "locked_quantity", "total_quantity", "created_at", "updated_at"]
