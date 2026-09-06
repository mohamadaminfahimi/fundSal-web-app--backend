from __future__ import annotations

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """JWT را از Cookie می‌خواند و از ذخیره‌سازی توکن در localStorage جلوگیری می‌کند."""

    def authenticate(self, request):
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
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
    """در خروج، Cookie ها را پاک می‌کند تا استفاده مجدد از توکن متوقف شود."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
