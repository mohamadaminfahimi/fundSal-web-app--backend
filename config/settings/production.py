# config/settings/production.py
"""
تنظیمات مخصوص محیط تولید (production).

اجرا با:
    DJANGO_SETTINGS_MODULE=config.settings.production

هرگز DEBUG=True در این فایل قرار نمی‌گیرد؛ فعال بودن Debug در production
باعث افشای Stack Trace، مسیرهای فایل، و بخشی از تنظیمات حساس می‌شود.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# WhiteNoise بلافاصله بعد از SecurityMiddleware قرار می‌گیرد.
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

# ✅ HSTS
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# پشت Reverse Proxy مثل Nginx
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ---------------------------------------------------------------------------
# CORS (production) — فقط دامنه‌های واقعی
# ---------------------------------------------------------------------------

# ✅ حتماً از env بخوانید، نه دامنه‌های تست
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# ---------------------------------------------------------------------------
# Logging (production)
# ---------------------------------------------------------------------------

LOGGING["root"]["level"] = "WARNING"  # noqa: F405
LOGGING["loggers"]["django"]["level"] = "WARNING"  # noqa: F405