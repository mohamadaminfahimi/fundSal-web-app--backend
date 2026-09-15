# apps/users/serializers.py

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


# ============================================================
# User Serializer
# ============================================================

class UserSerializer(serializers.ModelSerializer):
    """سریالایزر کاربر — با فیلد name"""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "is_active",
            "is_staff",
            "is_email_verified",
            "date_joined",
        ]
        read_only_fields = ["id", "date_joined", "is_email_verified"]

    def get_full_name(self, obj):
        return obj.name or obj.email or ""


# ============================================================
# Register Serializer
# ============================================================

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=10)

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "first_name",
            "last_name",
            "phone_number",
        ]

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("این ایمیل قبلاً ثبت شده است.")
        return value

    def validate_phone_number(self, value):
        if not value:
            return value
        digits = "".join(c for c in value if c.isdigit())
        if digits.startswith("0"):
            digits = digits[1:]
        if digits.startswith("98") and len(digits) > 10:
            digits = digits[2:]
        if len(digits) != 10:
            raise serializers.ValidationError("شماره موبایل معتبر نیست.")
        intl = "+98" + digits
        if User.objects.filter(phone_number=intl).exists():
            raise serializers.ValidationError("این شماره موبایل قبلاً ثبت شده است.")
        return intl

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


# ============================================================
# Login Serializer
# ============================================================

class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone_number = (attrs.get("phone_number") or "").strip()
        email = (attrs.get("email") or "").strip().lower()
        password = attrs.get("password")

        if not password:
            raise serializers.ValidationError({"password": "رمز عبور الزامی است."})

        user = None

        if phone_number:
            digits = "".join(c for c in phone_number if c.isdigit())
            if digits.startswith("0"):
                digits = digits[1:]
            if digits.startswith("98") and len(digits) > 10:
                digits = digits[2:]
            intl = "+98" + digits
            local = "0" + digits
            user = User.objects.filter(
                phone_number__in=[intl, local]
            ).first()
        elif email:
            user = User.objects.filter(email__iexact=email).first()
        else:
            raise serializers.ValidationError({"detail": "شماره موبایل یا ایمیل الزامی است."})

        if not user:
            raise serializers.ValidationError({"detail": "کاربری با این مشخصات یافت نشد."})

        if not user.check_password(password):
            raise serializers.ValidationError({"password": "رمز عبور اشتباه است."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "حساب کاربری غیرفعال است."})

        attrs["user"] = user
        return attrs


# ============================================================
# Profile Update Serializer
# ============================================================

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name", "phone_number"]

    def validate_phone_number(self, value):
        if not value:
            return value

        digits = "".join(c for c in value if c.isdigit())
        if digits.startswith("0"):
            digits = digits[1:]
        if digits.startswith("98") and len(digits) > 10:
            digits = digits[2:]
        if len(digits) != 10:
            raise serializers.ValidationError("شماره موبایل معتبر نیست.")

        intl = "+98" + digits
        qs = User.objects.filter(phone_number=intl)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError("این شماره موبایل قبلاً ثبت شده است.")
        return intl