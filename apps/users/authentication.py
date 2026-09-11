# apps/users/authentication.py

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)

User = get_user_model()


class CookieJWTAuthentication(JWTAuthentication):
    """
    احراز هویت JWT از Cookie.
    
    بهینه‌سازی‌ها:
    - کش کردن user به مدت ۵ دقیقه (جلوگیری از کوئری تکراری)
    - only() برای خواندن فقط فیلدهای لازم
    - پشتیبانی همزمان از Cookie و Header (fallback)
    """

    def authenticate(self, request):
        # ✅ تلاش اول: از Cookie
        raw_token = request.COOKIES.get("access_token")
        
        # ✅ اگر در Cookie نبود، از Header بگیر (fallback)
        if raw_token is None:
            header = self.get_header(request)
            if header is None:
                return None
            raw_token = self.get_raw_token(header)
            if raw_token is None:
                return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except (InvalidToken, TokenError):
            return None

        # ✅ کش user به مدت ۵ دقیقه
        user_id = validated_token.get("user_id")
        cache_key = f"auth:user:{user_id}"
        
        user = cache.get(cache_key)
        if user is None:
            try:
                user = User.objects.only(
                    "id",
                    "email",
                    "first_name",
                    "last_name",
                    "is_active",
                    "is_staff",
                    "is_email_verified",
                ).get(id=user_id)
                cache.set(cache_key, user, 300)  # ۵ دقیقه
                logger.debug(f"💾 Auth user {user_id} loaded from DB")
            except User.DoesNotExist:
                return None
        else:
            logger.debug(f"⚡ Auth user {user_id} loaded from cache")

        return user, validated_token


def set_auth_cookies(response, access_token: str, refresh_token: str) -> None:
    """توکن‌ها را در HttpOnly Cookie امن قرار می‌دهد."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        max_age=15 * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )


def clear_auth_cookies(response) -> None:
    """در خروج، Cookie ها را پاک می‌کند."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")