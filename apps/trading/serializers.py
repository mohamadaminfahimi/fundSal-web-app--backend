# apps/trading/serializers.py

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    """سریالایزر سفارش — با اطلاعات کامل برای UI کاربر"""

    # ✅ اطلاعات فلز
    metal_label = serializers.SerializerMethodField()

    # ✅ اطلاعات کاربر
    user_email = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()

    # ✅ توضیحات ادمین (از metadata)
    admin_note = serializers.SerializerMethodField()

    # ✅ تاریخ بررسی
    reviewed_at = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "metal_code",
            "metal_label",
            "side",
            "order_type",
            "quantity",
            "remaining_quantity",
            "price_per_gram",
            "total_amount",
            "status",
            "admin_note",
            "reviewed_at",
            "user_email",
            "user_name",
            "created_at",
            "updated_at",
            "metadata",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def get_metal_label(self, obj):
        return {
            "GOLD": "طلا",
            "SILVER": "نقره",
        }.get(obj.metal_code, obj.metal_code)

    def get_user_email(self, obj):
        return obj.user.email if obj.user else None

    def get_user_name(self, obj):
        if not obj.user:
            return None
        name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return name or obj.user.email

    def get_admin_note(self, obj):
        """توضیحات ادمین از metadata خوانده می‌شود"""
        meta = obj.metadata or {}
        return meta.get("admin_note", "")

    def get_reviewed_at(self, obj):
        meta = obj.metadata or {}
        return meta.get("reviewed_at", None)


class CreateOrderSerializer(serializers.Serializer):
    """سریالایزر ساخت سفارش"""

    metal_code = serializers.ChoiceField(
        choices=["GOLD", "SILVER"],
        required=True,
        error_messages={
            "invalid_choice": "نوع فلز باید GOLD یا SILVER باشد.",
            "required": "نوع فلز الزامی است.",
        },
    )

    quantity = serializers.DecimalField(
        max_digits=20,
        decimal_places=8,
        required=True,
        min_value=Decimal("0.0001"),
        error_messages={
            "min_value": "حداقل مقدار ۰.۰۰۰۱ گرم است.",
            "required": "مقدار الزامی است.",
        },
    )

    price_per_gram = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        required=True,
        min_value=Decimal("1000"),
        error_messages={
            "min_value": "قیمت هر گرم باید حداقل ۱,۰۰۰ تومان باشد.",
            "required": "قیمت هر گرم الزامی است.",
        },
    )