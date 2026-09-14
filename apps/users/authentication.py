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
    احراز هویت با JWT از طریق HttpOnly Cookie.

    اول access_token را از Cookie می‌خواند.
    اگر Cookie وجود نداشت، Authorization Header را بررسی می‌کند
    تا در صورت نیاز سازگاری با Bearer Token نیز حفظ شود.
    """

    def authenticate(self, request):
        # ---------------------------------------------------------
        # 1. دریافت Access Token از Cookie
        # ---------------------------------------------------------
        raw_token = request.COOKIES.get("access_token")

        logger.debug(
            "[AUTH] Cookies received: %s",
            list(request.COOKIES.keys()),
        )

        if raw_token:
            logger.debug("[AUTH] access_token found in cookie")
        else:
            logger.debug("[AUTH] access_token NOT found in cookie")

        # ---------------------------------------------------------
        # 2. اگر Cookie نبود، Authorization Header را بررسی کن
        # ---------------------------------------------------------
        if raw_token is None:
            header = self.get_header(request)

            if header is None:
                logger.debug(
                    "[AUTH] No access token in cookie or Authorization header"
                )
                return None

            logger.debug("[AUTH] Authorization header found")

            raw_token = self.get_raw_token(header)

            if raw_token is None:
                logger.debug(
                    "[AUTH] Authorization header does not contain a valid Bearer token"
                )
                return None

        # ---------------------------------------------------------
        # 3. اعتبارسنجی JWT
        # ---------------------------------------------------------
        try:
            validated_token = self.get_validated_token(raw_token)

            logger.debug("[AUTH] JWT validated successfully")

        except (InvalidToken, TokenError) as exc:
            logger.warning(
                "[AUTH] JWT validation failed: %s",
                str(exc),
            )
            return None

        # ---------------------------------------------------------
        # 4. استخراج User ID
        # ---------------------------------------------------------
        user_id = validated_token.get("user_id")

        if not user_id:
            logger.warning(
                "[AUTH] JWT does not contain user_id"
            )
            return None

        logger.debug(
            "[AUTH] Authenticated user_id: %s",
            user_id,
        )

        # ---------------------------------------------------------
        # 5. دریافت User از Cache
        # ---------------------------------------------------------
        cache_key = f"auth:user:{user_id}"

        user = cache.get(cache_key)

        if user is not None:
            logger.debug(
                "[AUTH] User loaded from cache: %s",
                user_id,
            )

        # ---------------------------------------------------------
        # 6. اگر در Cache نبود، از Database بخوان
        # ---------------------------------------------------------
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

                # Cache به مدت 5 دقیقه
                cache.set(
                    cache_key,
                    user,
                    300,
                )

                logger.debug(
                    "[AUTH] User loaded from database: %s",
                    user_id,
                )

            except User.DoesNotExist:
                logger.warning(
                    "[AUTH] User does not exist: %s",
                    user_id,
                )
                return None

        # ---------------------------------------------------------
        # 7. بررسی فعال بودن کاربر
        # ---------------------------------------------------------
        if not user.is_active:
            logger.warning(
                "[AUTH] User is inactive: %s",
                user_id,
            )
            return None

        # ---------------------------------------------------------
        # 8. Authentication موفق
        # ---------------------------------------------------------
        logger.debug(
            "[AUTH] Authentication successful for user: %s",
            user_id,
        )

        return user, validated_token


def set_auth_cookies(
    response,
    access_token: str,
    refresh_token: str,
) -> None:
    """
    ذخیره JWT ها در HttpOnly Cookie.

    Access Token:
        15 دقیقه

    Refresh Token:
        7 روز
    """

    # ---------------------------------------------------------
    # Access Token
    # ---------------------------------------------------------
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        max_age=15 * 60,
        path="/",
    )

    # ---------------------------------------------------------
    # Refresh Token
    # ---------------------------------------------------------
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )


def clear_auth_cookies(response):
    """
    پاک کردن کامل کوکی‌های احراز هویت.
    """
    # روش استاندارد
    response.delete_cookie(
        "access_token",
        path="/",
        samesite="Lax",
    )
    response.delete_cookie(
        "refresh_token",
        path="/",
        samesite="Lax",
    )

    # روش مطمئن‌تر برای برخی مرورگرها
    response.set_cookie(
        key="access_token",
        value="",
        max_age=0,
        expires="Thu, 01 Jan 1970 00:00:00 GMT",
        path="/",
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
    )
    response.set_cookie(
        key="refresh_token",
        value="",
        max_age=0,
        expires="Thu, 01 Jan 1970 00:00:00 GMT",
        path="/",
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
    )

    

    response.delete_cookie(
        "refresh_token",
        path="/",
    )