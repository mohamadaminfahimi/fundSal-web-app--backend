"""
تنظیمات مخصوص محیط تولید (production).

اجرا با:
    DJANGO_SETTINGS_MODULE=config.settings.production

هرگز DEBUG=True در این فایل قرار نمی‌گیرد؛ فعال بودن Debug در production
باعث افشای Stack Trace، مسیرهای فایل، و بخشی از تنظیمات حساس به هر کاربر
خطایابی‌شده می‌شود (Sensitive Data Exposure).
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# WhiteNoise بلافاصله بعد از SecurityMiddleware قرار می‌گیرد تا فایل‌های
# static قبل از رسیدن به بقیه‌ی Middleware Stack مستقیماً سرو شوند؛
# این باعث می‌شود نیازی به Nginx برای سرو کردن static نباشد (اختیاری).
MIDDLEWARE = (
    MIDDLEWARE[:1]  # noqa: F405
    + ["whitenoise.middleware.WhiteNoiseMiddleware"]
    + MIDDLEWARE[1:]  # noqa: F405
)

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

# ---------------------------------------------------------------------------
# HTTPS / Cookie Security
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# HSTS به مرورگر می‌گوید که برای مدت مشخصی فقط از HTTPS با این دامنه صحبت کند؛
# این از Downgrade Attack به HTTP جلوگیری می‌کند.
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# پشت یک Reverse Proxy مثل Nginx، Django باید بداند که هدر
# X-Forwarded-Proto نشان‌دهنده‌ی پروتکل واقعی (https) است، وگرنه
# SECURE_SSL_REDIRECT باعث یک Redirect Loop بی‌نهایت می‌شود.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# Static files (whitenoise در Phase 22 به Middleware اضافه می‌شود)
# ---------------------------------------------------------------------------

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

LOGGING["root"]["level"] = "WARNING"  # noqa: F405
