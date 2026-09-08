from __future__ import annotations

from django.conf import settings
from django.contrib.auth import logout
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from .authentication import clear_auth_cookies, set_auth_cookies
from .serializers import LoginSerializer, ProfileUpdateSerializer, RegisterSerializer, UserSerializer


class ErrorDetail:
    """کلاس مدیریت خطاها با راهنمای فارسی"""
    
    ERROR_MESSAGES = {
        # خطاهای احراز هویت
        "AUTH_001": "نام کاربری یا رمز عبور اشتباه است. لطفاً دقت کنید.",
        "AUTH_002": "حساب کاربری شما غیرفعال شده است. با پشتیبانی تماس بگیرید.",
        "AUTH_003": "برای دسترسی به این بخش باید وارد شوید.",
        "AUTH_004": "نشست شما منقضی شده است. دوباره وارد شوید.",
        
        # خطاهای توکن
        "TOKEN_001": "توکن دسترسی معتبر نیست یا منقضی شده است.",
        "TOKEN_002": "توکن بازیابی نامعتبر است. دوباره تلاش کنید.",
        "TOKEN_003": "توکن بازیابی یافت نشد. لطفاً وارد شوید.",
        "TOKEN_004": "فرمت توکن اشتباه است.",
        
        # خطاهای ثبت‌نام
        "REG_001": "این نام کاربری قبلاً ثبت شده است.",
        "REG_002": "این ایمیل قبلاً ثبت شده است.",
        "REG_003": "رمز عبور باید حداقل ۸ کاراکتر باشد.",
        "REG_004": "رمز عبور باید شامل حروف بزرگ و کوچک و عدد باشد.",
        "REG_005": "رمز عبور و تکرار آن مطابقت ندارند.",
        "REG_006": "فرمت ایمیل معتبر نیست.",
        "REG_007": "شماره تلفن قبلاً ثبت شده است.",
        "REG_008": "فرمت شماره تلفن معتبر نیست. مثال: +989123456789",
        
        # خطاهای ورودی
        "INP_001": "تمام فیلدهای ضروری را پر کنید.",
        "INP_002": "مقدار وارد شده معتبر نیست.",
        "INP_003": "طول متن بیش از حد مجاز است.",
        
        # خطاهای عمومی
        "GEN_001": "خطای داخلی سرور. لطفاً دوباره تلاش کنید.",
        "GEN_002": "درخواست نامعتبر است.",
        "GEN_003": "شما دسترسی به این عملیات را ندارید.",
        
        # خطاهای پروفایل
        "PROF_001": "امکان ویرایش این فیلد وجود ندارد.",
        "PROF_002": "اطلاعات وارد شده برای پروفایل صحیح نیست.",
    }
    
    @classmethod
    def get_message(cls, code: str, default: str = None) -> str:
        """دریافت پیام خطا با کد"""
        return cls.ERROR_MESSAGES.get(code, default or "خطای ناشناخته رخ داده است.")
    
    @classmethod
    def format_error(cls, code: str, field: str = None, detail: str = None) -> dict:
        """قالب‌بندی استاندارد خطا"""
        error = {
            "success": False,
            "error": {
                "code": code,
                "message": cls.get_message(code),
            }
        }
        if field:
            error["error"]["field"] = field
        if detail:
            error["error"]["detail"] = detail
        return error


class CustomResponse:
    """کلاس کمکی برای تولید پاسخ‌های استاندارد"""
    
    @staticmethod
    def success(data: dict = None, message: str = "عملیات با موفقیت انجام شد.", status_code: int = status.HTTP_200_OK) -> Response:
        return Response(
            {
                "success": True,
                "message": message,
                "data": data or {},
            },
            status=status_code
        )
    
    @staticmethod
    def error(code: str, field: str = None, detail: str = None, status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
        return Response(
            ErrorDetail.format_error(code, field, detail),
            status=status_code
        )
    
    @classmethod
    def validation_errors(cls, serializer_errors: dict) -> Response:
        """تبدیل خطاهای اعتبارسنجی سریالایزر به فرمت استاندارد"""
        formatted_errors = []
        
        for field, errors in serializer_errors.items():
            for error in errors:
                error_message = str(error)
                error_code = cls._get_error_code(field, error_message)
                
                error_display_message = ErrorDetail.get_message(error_code, error_message)
                
                formatted_errors.append({
                    "field": field,
                    "code": error_code,
                    "message": error_display_message,
                    "original": error_message
                })
        
        main_message = cls._get_error_summary(formatted_errors)
        
        return Response(
            {
                "success": False,
                "errors": formatted_errors,
                "count": len(formatted_errors),
                "message": main_message
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @classmethod
    def _get_error_code(cls, field: str, error_message: str) -> str:
        """تشخیص کد خطا بر اساس فیلد و پیام"""
        error_message_lower = error_message.lower()
        
        # خطاهای detail (لاگین)
        if "detail" in field:
            if "email" in error_message_lower or "password" in error_message_lower or "رمز" in error_message:
                return "AUTH_001"
        
        # خطاهای شماره تلفن
        elif "phone" in field.lower() or "phone_number" in field.lower():
            if "already exists" in error_message_lower or "قبلاً ثبت" in error_message:
                return "REG_007"
            if "format" in error_message_lower or "معتبر" in error_message:
                return "REG_008"
            if "required" in error_message_lower:
                return "INP_001"
        
        # خطاهای رمز عبور
        elif "password" in field.lower():
            if "length" in error_message_lower or "کاراکتر" in error_message:
                return "REG_003"
            if "match" in error_message_lower or "مطابقت" in error_message:
                return "REG_005"
            if "common" in error_message_lower or "ساده" in error_message:
                return "REG_004"
            if "numeric" in error_message_lower or "عددی" in error_message:
                return "REG_004"
        
        # خطاهای ایمیل
        elif "email" in field.lower():
            if "valid" in error_message_lower or "معتبر" in error_message:
                return "REG_006"
            if "exists" in error_message_lower or "قبلاً ثبت" in error_message:
                return "REG_002"
        
        # خطاهای نام کاربری
        elif "username" in field.lower():
            if "exists" in error_message_lower or "قبلاً ثبت" in error_message:
                return "REG_001"
        
        # خطاهای ضروری
        elif "required" in error_message_lower:
            return "INP_001"
        
        # پیش‌فرض
        return "INP_002"
    
    @classmethod
    def _get_error_summary(cls, errors: list) -> str:
        """ایجاد خلاصه خطا"""
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


class RegisterView(GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            
            if not serializer.is_valid():
                # نمایش خطاهای اعتبارسنجی با جزئیات کامل
                print("=" * 50)
                print("REGISTER VALIDATION ERRORS:")
                print("=" * 50)
                for field, errors in serializer.errors.items():
                    print(f"📌 {field}:")
                    for error in errors:
                        print(f"   ❌ {error}")
                print("=" * 50)
                
                return CustomResponse.validation_errors(serializer.errors)

            user = serializer.save()
            
            # لاگ ثبت‌نام موفق - اصلاح شده برای کاربر بدون username
            user_identifier = user.email if hasattr(user, 'email') else str(user.id)
            print(f"✅ کاربر جدید ثبت نام کرد: {user_identifier}")
            
            return CustomResponse.success(
                data=UserSerializer(user).data,
                message="ثبت نام با موفقیت انجام شد.",
                status_code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            # خطای غیرمنتظره
            print(f"🔥 خطای غیرمنتظره در RegisterView: {str(e)}")
            return CustomResponse.error(
                code="GEN_001",
                detail=str(e) if settings.DEBUG else None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LoginView(GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data, context={"request": request})
            
            if not serializer.is_valid():
                print("=" * 50)
                print("LOGIN VALIDATION ERRORS:")
                print("=" * 50)
                for field, errors in serializer.errors.items():
                    print(f"📌 {field}:")
                    for error in errors:
                        print(f"   ❌ {error}")
                print("=" * 50)
                return CustomResponse.validation_errors(serializer.errors)
            
            user = serializer.validated_data.get("user")
            
            if not user:
                return CustomResponse.error(
                    code="AUTH_001",
                    status_code=status.HTTP_401_UNAUTHORIZED
                )
            
            if not user.is_active:
                return CustomResponse.error(
                    code="AUTH_002",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # تولید توکن‌ها
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # لاگ ورود موفق - اصلاح شده برای کاربر بدون username
            user_identifier = user.email if hasattr(user, 'email') else str(user.id)
            print(f"✅ کاربر وارد شد: {user_identifier} - IP: {request.META.get('REMOTE_ADDR')}")
            
            response = CustomResponse.success(
                data={
                    "user": UserSerializer(user).data,
                    "access_expires_at": timezone.now() + settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"],
                    "refresh_expires_at": timezone.now() + settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"],
                },
                message="ورود با موفقیت انجام شد."
            )
            
            # تنظیم کوکی‌های امن
            set_auth_cookies(response, access_token, refresh_token)
            return response
            
        except Exception as e:
            print(f"🔥 خطای غیرمنتظره در LoginView: {str(e)}")
            return CustomResponse.error(
                code="GEN_001",
                detail=str(e) if settings.DEBUG else None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            # لاگ خروج - اصلاح شده برای کاربر بدون username
            user_identifier = request.user.email if hasattr(request.user, 'email') else str(request.user.id)
            print(f"✅ کاربر خارج شد: {user_identifier}")
            
            logout(request)
            response = CustomResponse.success(
                message="خروج با موفقیت انجام شد."
            )
            clear_auth_cookies(response)
            return response
            
        except Exception as e:
            print(f"🔥 خطای غیرمنتظره در LogoutView: {str(e)}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            
            # بررسی وجود توکن
            if not refresh_token:
                print("⚠️ تلاش برای رفرش بدون توکن")
                return CustomResponse.error(
                    code="TOKEN_003",
                    status_code=status.HTTP_401_UNAUTHORIZED
                )
            
            # بررسی معتبر بودن توکن
            try:
                refresh = RefreshToken(refresh_token)
            except TokenError as e:
                print(f"⚠️ توکن رفرش نامعتبر: {str(e)}")
                return CustomResponse.error(
                    code="TOKEN_002",
                    detail=str(e),
                    status_code=status.HTTP_401_UNAUTHORIZED
                )
            except InvalidToken as e:
                print(f"⚠️ توکن رفرش نامعتبر: {str(e)}")
                return CustomResponse.error(
                    code="TOKEN_004",
                    detail=str(e),
                    status_code=status.HTTP_401_UNAUTHORIZED
                )
            
            # تولید توکن جدید
            access_token = str(refresh.access_token)
            
            print(f"✅ توکن جدید صادر شد")
            
            response = CustomResponse.success(
                data={
                    "access_token": access_token,
                    "access_expires_at": timezone.now() + settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"],
                },
                message="توکن با موفقیت به‌روزرسانی شد."
            )
            
            # تنظیم کوکی جدید
            set_auth_cookies(response, access_token, str(refresh))
            return response
            
        except Exception as e:
            print(f"🔥 خطای غیرمنتظره در RefreshTokenView: {str(e)}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            return CustomResponse.success(
                data=UserSerializer(request.user).data,
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
            serializer = ProfileUpdateSerializer(
                request.user, 
                data=request.data, 
                partial=True,
                context={"request": request}
            )
            
            if not serializer.is_valid():
                print("=" * 50)
                print("PROFILE UPDATE VALIDATION ERRORS:")
                print("=" * 50)
                for field, errors in serializer.errors.items():
                    print(f"📌 {field}:")
                    for error in errors:
                        print(f"   ❌ {error}")
                print("=" * 50)
                return CustomResponse.validation_errors(serializer.errors)
            
            # بررسی تغییرات
            updated_user = serializer.save()
            changed_fields = list(serializer.validated_data.keys())
            
            # لاگ به‌روزرسانی - اصلاح شده برای کاربر بدون username
            user_identifier = request.user.email if hasattr(request.user, 'email') else str(request.user.id)
            print(f"✅ پروفایل به‌روز شد: {user_identifier} - تغییرات: {', '.join(changed_fields)}")
            
            return CustomResponse.success(
                data=UserSerializer(updated_user).data,
                message=f"پروفایل با موفقیت به‌روزرسانی شد. ({len(changed_fields)} تغییر)"
            )
            
        except Exception as e:
            print(f"🔥 خطای غیرمنتظره در ProfileView PATCH: {str(e)}")
            return CustomResponse.error(
                code="GEN_001",
                detail=str(e) if settings.DEBUG else None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# کلاس کمکی برای نمایش لاگ‌های زیبا
class ViewLogger:
    @staticmethod
    def log_request(request, view_name: str):
        """لاگ درخواست ورودی"""
        user_identifier = "ناشناس"
        if request.user.is_authenticated:
            user_identifier = request.user.email if hasattr(request.user, 'email') else str(request.user.id)
            
        print(f"""
        ========================================
        📝 {view_name}
        ⏰ {timezone.now()}
        👤 کاربر: {user_identifier}
        🌐 IP: {request.META.get('REMOTE_ADDR')}
        📌 متد: {request.method}
        📂 مسیر: {request.path}
        ========================================
        """)