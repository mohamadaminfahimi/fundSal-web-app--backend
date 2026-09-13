# apps/users/serializers.py

from __future__ import annotations

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

User = get_user_model()


# ============================================================
# Auth Serializers
# ============================================================

class RegisterSerializer(serializers.ModelSerializer):
    """سریالایزر ثبت‌نام"""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=False,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "phone_number",
        ]
        extra_kwargs = {
            "email": {
                "validators": [
                    UniqueValidator(
                        queryset=User.objects.all(),
                        message="این ایمیل قبلاً ثبت شده است.",
                    )
                ],
            },
            "phone_number": {
                "required": False,
                "allow_blank": True,
                "allow_null": True,
            },
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
        }

    def validate_email(self, value: str) -> str:
        return value.lower().strip()

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")

        if password_confirm and password != password_confirm:
            raise serializers.ValidationError(
                {"password_confirm": "رمزهای عبور مطابقت ندارند."}
            )

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm", None)
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """سریالایزر ورود"""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        email = attrs.get("email", "").lower().strip()
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError(
                {"detail": "ایمیل و رمز عبور الزامی است."}
            )

        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )

        if not user:
            raise serializers.ValidationError(
                {"detail": "ایمیل یا رمز عبور اشتباه است."}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "حساب کاربری شما غیرفعال شده است."}
            )

        attrs["user"] = user
        return attrs


# ============================================================
# User Serializers
# ============================================================

class UserSerializer(serializers.ModelSerializer):
    """سریالایزر پایه برای نمایش کاربر"""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "is_email_verified",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "phone_number",
            "is_email_verified",
            "date_joined",
        ]

    def get_full_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}".strip()

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    سریالایزر ویرایش پروفایل
    """
    
    email = serializers.EmailField(
        required=False,
        allow_blank=False,
        # ✅ UniqueValidator رو حذف کن (توی validate_email چک میشه)
    )
    
    first_name = serializers.CharField(
        required=False,
        max_length=150,
        allow_blank=True,
    )
    
    last_name = serializers.CharField(
        required=False,
        max_length=150,
        allow_blank=True,
    )
    
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
    
    def validate_email(self, value: str) -> str:
        if not value:
            return value
        
        normalized = value.lower().strip()
        
        request = self.context.get("request")
        current_user = request.user if request else None
        
        query = User.objects.filter(email__iexact=normalized)
        if current_user and current_user.is_authenticated:
            query = query.exclude(id=current_user.id)
        
        if query.exists():
            raise serializers.ValidationError("این ایمیل قبلاً ثبت شده است.")
        
        return normalized
    
    def validate_first_name(self, value: str) -> str:
        return value.strip() if value else value
    
    def validate_last_name(self, value: str) -> str:
        return value.strip() if value else value
    
    def update(self, instance, validated_data):
        email_changed = (
            "email" in validated_data
            and validated_data["email"] != instance.email
        )
        
        if "first_name" in validated_data:
            instance.first_name = validated_data["first_name"]
        
        if "last_name" in validated_data:
            instance.last_name = validated_data["last_name"]
        
        if "email" in validated_data:
            instance.email = validated_data["email"]
            if email_changed:
                instance.is_email_verified = False
        
        instance.save()
        return instance