from __future__ import annotations

from rest_framework import serializers

from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "metal_code",
            "side",
            "order_type",
            "quantity",
            "remaining_quantity",
            "price_per_gram",
            "total_amount",
            "idempotency_key",
            "status",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "remaining_quantity",
            "total_amount",
            "idempotency_key",
            "status",
            "created_at",
            "updated_at",
        ]
