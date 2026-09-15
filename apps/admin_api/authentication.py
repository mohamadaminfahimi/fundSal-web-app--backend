from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)
User = get_user_model()


class AdminCookieJWTAuthentication(JWTAuthentication):
    """
    احراز هویت ادمین از Cookie admin_access_token یا هدر Authorization.
    فقط کاربرانی که is_staff=True و is_active=True هستند قبول می‌شوند.
    """

    def authenticate(self, request):
        # 1) اول از کوکی ادمین
        raw_token = request.COOKIES.get(settings.ADMIN_ACCESS_COOKIE)

        # 2) اگر نبود، از هدر Authorization
        if raw_token is None:
            header = self.get_header(request)
            if header is not None:
                raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        # 3) اعتبارسنجی
        try:
            validated_token = self.get_validated_token(raw_token)
        except (InvalidToken, TokenError):
            return None

        user_id = validated_token.get("user_id")
        if not user_id:
            return None

        # 4) کش
        cache_key = f"admin:user:{user_id}"
        user = cache.get(cache_key)

        if user is None:
            try:
                user = User.objects.only(
                    "id",
                    "email",
                    "name",
                    "is_active",
                    "is_staff",
                ).get(id=user_id)
                
                cache.set(cache_key, user, 300)

            except User.DoesNotExist:
                return None

        # 5) چک is_staff و is_active
        if not user.is_staff or not user.is_active:
            return None

        return user, validated_token