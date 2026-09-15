# apps/users/views.py

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import get_user_model, logout
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from .authentication import clear_auth_cookies, set_auth_cookies
from .serializers import (
    LoginSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


# ============================================================
# Error & Response Helpers
# ============================================================

class ErrorDetail:
    """کلاس مدیریت خطاها با راهنمای فارسی"""

    ERROR_MESSAGES = {
        "AUTH_001": "نام کاربری یا رمز عبور اشتباه است. لطفاً دقت کنید.",
        "AUTH_002": "حساب کاربری شما غیرفعال شده است. با پشتیبانی تماس بگیرید.",
        "AUTH_003": "برای دسترسی به این بخش باید وارد شوید.",
        "AUTH_004": "نشست شما منقضی شده است. دوباره وارد شوید.",
        "AUTH_005": "این شماره موبایل در سیستم ثبت نشده است. برای ثبت‌نام با پشتیبانی تماس بگیرید.",
        "TOKEN_001": "توکن دسترسی معتبر نیست یا منقضی شده است.",
        "TOKEN_002": "توکن بازیابی نامعتبر است. دوباره تلاش کنید.",
        "TOKEN_003": "توکن بازیابی یافت نشد. لطفاً وارد شوید.",
        "TOKEN_004": "فرمت توکن اشتباه است.",
        "REG_001": "این نام کاربری قبلاً ثبت شده است.",
        "REG_002": "این ایمیل قبلاً ثبت شده است.",
        "REG_003": "رمز عبور باید حداقل ۸ کاراکتر باشد.",
        "REG_004": "رمز عبور باید شامل حروف بزرگ و کوچک و عدد باشد.",
        "REG_005": "رمز عبور و تکرار آن مطابقت ندارند.",
        "REG_006": "فرمت ایمیل معتبر نیست.",
        "REG_007": "شماره تلفن قبلاً ثبت شده است.",
        "REG_008": "فرمت شماره تلفن معتبر نیست. مثال: +989123456789",
        "INP_001": "تمام فیلدهای ضروری را پر کنید.",
        "INP_002": "مقدار وارد شده معتبر نیست.",
        "INP_003": "طول متن بیش از حد مجاز است.",
        "GEN_001": "خطای داخلی سرور. لطفاً دوباره تلاش کنید.",
        "GEN_002": "درخواست نامعتبر است.",
        "GEN_003": "شما دسترسی به این عملیات را ندارید.",
        "PROF_001": "امکان ویرایش این فیلد وجود ندارد.",
        "PROF_002": "اطلاعات وارد شده برای پروفایل صحیح نیست.",
    }

    @classmethod
    def get_message(cls, code: str, default: str = None) -> str:
        return cls.ERROR_MESSAGES.get(code, default or "خطای ناشناخته رخ داده است.")

    @classmethod
    def format_error(cls, code: str, field: str = None, detail: str = None) -> dict:
        error = {
            "success": False,
            "error": {
                "code": code,
                "message": cls.get_message(code),
            },
        }
        if field:
            error["error"]["field"] = field
        if detail:
            error["error"]["detail"] = detail
        return error


class CustomResponse:
    """کلاس کمکی برای تولید پاسخ‌های استاندارد"""

    @staticmethod
    def success(
        data: dict = None,
        message: str = "عملیات با موفقیت انجام شد.",
        status_code: int = status.HTTP_200_OK,
    ) -> Response:
        return Response(
            {"success": True, "message": message, "data": data or {}},
            status=status_code,
        )

    @staticmethod
    def error(
        code: str,
        field: str = None,
        detail: str = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> Response:
        return Response(
            ErrorDetail.format_error(code, field, detail), status=status_code
        )

    @classmethod
    def validation_errors(cls, serializer_errors: dict) -> Response:
        formatted_errors = []

        for field, errors in serializer_errors.items():
            for error in errors:
                error_message = str(error)
                error_code = cls._get_error_code(field, error_message)
                error_display_message = ErrorDetail.get_message(error_code, error_message)

                formatted_errors.append(
                    {
                        "field": field,
                        "code": error_code,
                        "message": error_display_message,
                        "original": error_message,
                    }
                )

        main_message = cls._get_error_summary(formatted_errors)

        return Response(
            {
                "success": False,
                "errors": formatted_errors,
                "count": len(formatted_errors),
                "message": main_message,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @classmethod
    def _get_error_code(cls, field: str, error_message: str) -> str:
        error_message_lower = error_message.lower()

        if "detail" in field:
            if (
                "email" in error_message_lower
                or "password" in error_message_lower
                or "رمز" in error_message
            ):
                return "AUTH_001"

        elif "phone" in field.lower() or "phone_number" in field.lower():
            if "already exists" in error_message_lower or "قبلاً ثبت" in error_message:
                return "REG_007"
            if "format" in error_message_lower or "معتبر" in error_message:
                return "REG_008"
            if "required" in error_message_lower:
                return "INP_001"

        elif "password" in field.lower():
            if "length" in error_message_lower or "کاراکتر" in error_message:
                return "REG_003"
            if "match" in error_message_lower or "مطابقت" in error_message:
                return "REG_005"
            if "common" in error_message_lower or "ساده" in error_message:
                return "REG_004"
            if "numeric" in error_message_lower or "عددی" in error_message:
                return "REG_004"

        elif "email" in field.lower():
            if "valid" in error_message_lower or "معتبر" in error_message:
                return "REG_006"
            if "exists" in error_message_lower or "قبلاً ثبت" in error_message:
                return "REG_002"

        elif "username" in field.lower():
            if "exists" in error_message_lower or "قبلاً ثبت" in error_message:
                return "REG_001"

        elif "required" in error_message_lower:
            return "INP_001"

        return "INP_002"

    @classmethod
    def _get_error_summary(cls, errors: list) -> str:
        if not errors:
            return "خطا در ورودی‌ها وجود دارد."

        if len(errors) == 1:
            return errors[0]["message"]

        important_messages = []
        for error in errors:
            if error["code"] in ["REG_001", "REG_002", "REG_007", "REG_008"]:
                important_messages.append(error["message"])

        if important_messages:
            return " | ".join(important_messages)

        return f"{len(errors)} خطا در ورودی‌ها وجود دارد."


# ============================================================
# Views
# ============================================================


class RegisterView(GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)

            if not serializer.is_valid():
                return CustomResponse.validation_errors(serializer.errors)

            user = serializer.save()
            user_identifier = user.email if hasattr(user, "email") else str(user.id)
            print(f"✅ کاربر جدید ثبت نام کرد: {user_identifier}")

            return CustomResponse.success(
                data=UserSerializer(user).data,
                message="ثبت نام با موفقیت انجام شد.",
                status_code=status.HTTP_201_CREATED,
            )

        except Exception as e:
            print(f"🔥 خطای غیرمنتظره در RegisterView: {str(e)}")
            return CustomResponse.error(
                code="GEN_001",
                detail=str(e) if settings.DEBUG else None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CheckPhoneView(APIView):
    """POST /api/v1/auth/check-phone/ - بررسی وجود شماره موبایل"""
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            phone_number = (request.data.get("phone_number") or "").strip()

            if not phone_number:
                return CustomResponse.error(
                    code="INP_001",
                    detail="شماره موبایل الزامی است.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # ✅ نرمال‌سازی شماره
            digits = "".join(c for c in phone_number if c.isdigit())

            if digits.startswith("0"):
                digits = digits[1:]

            if digits.startswith("98") and len(digits) > 10:
                digits = digits[2:]

            if len(digits) != 10:
                return CustomResponse.error(
                    code="REG_008",
                    detail="شماره موبایل معتبر نیست. مثال: 9123456789",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            intl_phone = "+98" + digits
            local_phone = "0" + digits

            # ✅ جستجو با هر دو فرمت
            user = User.objects.filter(
                Q(phone_number=intl_phone) | Q(phone_number=local_phone)
            ).first()

            if not user:
                return CustomResponse.error(
                    code="AUTH_005",
                    detail="این شماره موبایل در سیستم ثبت نشده است. برای ثبت‌نام با پشتیبانی تماس بگیرید.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            if not user.is_active:
                return CustomResponse.error(
                    code="AUTH_002",
                    detail="حساب کاربری شما غیرفعال شده است. با پشتیبانی تماس بگیرید.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            return CustomResponse.success(
                data={
                    "phone_number": user.phone_number,
                    "exists": True,
                },
                message="شماره موبایل تایید شد.",
            )

        except Exception as e:
            logger.exception(f"❌ Error in CheckPhoneView: {e}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LoginView(GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(
                data=request.data, context={"request": request}
            )

            if not serializer.is_valid():
                return CustomResponse.validation_errors(serializer.errors)

            user = serializer.validated_data.get("user")

            if not user:
                return CustomResponse.error(
                    code="AUTH_001", status_code=status.HTTP_401_UNAUTHORIZED
                )

            if not user.is_active:
                return CustomResponse.error(
                    code="AUTH_002", status_code=status.HTTP_403_FORBIDDEN
                )

            # تولید توکن‌ها
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            user_identifier = user.email if hasattr(user, "email") else str(user.id)
            print(f"✅ کاربر وارد شد: {user_identifier}")

            response = CustomResponse.success(
                data={
                    "user": UserSerializer(user).data,
                    "access_expires_at": timezone.now()
                    + settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"],
                    "refresh_expires_at": timezone.now()
                    + settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"],
                },
                message="ورود با موفقیت انجام شد.",
            )

            # تنظیم کوکی‌های امن
            set_auth_cookies(response, access_token, refresh_token)
            return response

        except Exception as e:
            print(f"🔥 خطای غیرمنتظره در LoginView: {str(e)}")
            return CustomResponse.error(
                code="GEN_001",
                detail=str(e) if settings.DEBUG else None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        response = CustomResponse.success(
            message="خروج با موفقیت انجام شد."
        )
        clear_auth_cookies(response)
        return response


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.COOKIES.get("refresh_token")

            if not refresh_token:
                print("⚠️ تلاش برای رفرش بدون توکن")
                return CustomResponse.error(
                    code="TOKEN_003", status_code=status.HTTP_401_UNAUTHORIZED
                )

            try:
                refresh = RefreshToken(refresh_token)
            except TokenError as e:
                print(f"⚠️ توکن رفرش نامعتبر: {str(e)}")
                return CustomResponse.error(
                    code="TOKEN_002",
                    detail=str(e),
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            except InvalidToken as e:
                print(f"⚠️ توکن رفرش نامعتبر: {str(e)}")
                return CustomResponse.error(
                    code="TOKEN_004",
                    detail=str(e),
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            access_token = str(refresh.access_token)
            print("✅ توکن جدید صادر شد")

            response = CustomResponse.success(
                data={
                    "access_token": access_token,
                    "access_expires_at": timezone.now()
                    + settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"],
                },
                message="توکن با موفقیت به‌روزرسانی شد.",
            )

            set_auth_cookies(response, access_token, str(refresh))
            return response

        except Exception as e:
            print(f"🔥 خطای غیرمنتظره در RefreshTokenView: {str(e)}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            cache_key = f"profile:user:{user.id}"

            cached = cache.get(cache_key)
            if cached is not None:
                return CustomResponse.success(
                    data=cached,
                    message="اطلاعات پروفایل دریافت شد."
                )

            data = UserSerializer(user).data
            cache.set(cache_key, data, 300)

            return CustomResponse.success(
                data=data,
                message="اطلاعات پروفایل دریافت شد."
            )
        except Exception as e:
            print(f"🔥 خطای غیرمنتظره در ProfileView GET: {str(e)}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, *args, **kwargs):
        try:
            user = request.user

            serializer = ProfileUpdateSerializer(
                user,
                data=request.data,
                partial=True,
                context={"request": request},
            )

            if not serializer.is_valid():
                if "email" in serializer.errors:
                    return CustomResponse.error(
                        code="REG_002",
                        field="email",
                        detail="این ایمیل قبلاً ثبت شده است.",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
                return CustomResponse.validation_errors(serializer.errors)

            changed_fields = list(serializer.validated_data.keys())
            if not changed_fields:
                return CustomResponse.error(
                    code="INP_002",
                    detail="هیچ تغییری اعمال نشد.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            updated_user = serializer.save()
            email_changed = "email" in changed_fields

            cache.delete(f"profile:user:{user.id}")
            cache.delete(f"dashboard:user:{user.id}")
            cache.delete(f"auth:user:{user.id}")

            user_identifier = user.phone_number
            print(f"✅ پروفایل به‌روز شد: {user_identifier} - تغییرات: {', '.join(changed_fields)}")

            message = f"پروفایل با موفقیت به‌روزرسانی شد. ({len(changed_fields)} تغییر)"
            if email_changed:
                message += " لطفاً ایمیل جدید خود را تایید کنید."

            return CustomResponse.success(
                data=UserSerializer(updated_user).data,
                message=message,
            )

        except Exception as e:
            print(f"🔥 خطای غیرمنتظره در ProfileView PATCH: {str(e)}")
            return CustomResponse.error(
                code="GEN_001",
                detail=str(e) if settings.DEBUG else None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )