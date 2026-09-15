# config/settings/base.py
"""
تنظیمات مشترک بین تمام محیط‌ها (development / production).

هیچ مقدار حساس (secret) نباید مستقیماً در این فایل نوشته شود.
تمام مقادیر حساس یا وابسته به محیط از طریق Environment Variable خوانده می‌شوند
تا امکان Secret Leakage از طریق Git وجود نداشته باشد.
"""

from datetime import timedelta
from pathlib import Path

import environ

# BASE_DIR به ریشه‌ی پروژه (پوشه‌ی backend/) اشاره می‌کند.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

# فایل .env فقط در development خوانده می‌شود.
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    environ.Env.read_env(str(ENV_FILE))


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = env("DJANGO_SECRET_KEY")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "corsheaders",
    # Local apps
    "apps.common",
    "apps.users",
    "apps.market",
    "apps.wallet",
    "apps.transactions",
    "apps.invoices",
    "apps.trading",
    "apps.admin_api",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CorsMiddleware باید پیش از CommonMiddleware قرار بگیرد تا هدرهای CORS
    # قبل از هرگونه Redirect یا پردازش دیگر روی Response اعمال شوند.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.RequestIDMiddleware",
    "apps.common.middleware.RequestTimingMiddleware",  # ✅ آخر
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        **env.db("DATABASE_URL"),
        "CONN_MAX_AGE": 600,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 5,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    }
}


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
)
CORS_ALLOW_CREDENTIALS = True

# ✅ هدرهایی که فرانت‌اند می‌تواند بفرستد
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# ✅ متدهای مجاز
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
)
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # تا فرانت‌اند بتواند بخواند (در صورت نیاز)
CSRF_COOKIE_SECURE = False   # در production True


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    # ✅ ترتیب مهم: Admin اول، چون کوکی admin_access_token را چک می‌کند
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.admin_api.authentication.AdminCookieJWTAuthentication",
        "apps.users.authentication.CookieJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "300/minute",
    },
    "EXCEPTION_HANDLER": "apps.common.exception_handler.custom_exception_handler",
}


# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------

SIMPLE_JWT = {
    # طول عمر کوتاه Access Token ریسک سرقت توکن را کاهش می‌دهد.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # چرخش خودکار Refresh Token همراه با Blacklist
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}


# ---------------------------------------------------------------------------
# drf-spectacular
# ---------------------------------------------------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE": "Precious Metals Trading Platform API",
    "DESCRIPTION": "API برای خرید، فروش و مدیریت طلا و نقره.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} - {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# ---------------------------------------------------------------------------
# Cache (Redis)
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "gold",
        "TIMEOUT": 300,
    }
}


# ---------------------------------------------------------------------------
# Cookie Names (سفارشی‌سازی‌شده برای ادمین و کاربر عادی)
# ---------------------------------------------------------------------------

# ✅ نام کوکی‌های کاربر عادی
USER_ACCESS_COOKIE = "access_token"
USER_REFRESH_COOKIE = "refresh_token"

# ✅ نام کوکی‌های ادمین
ADMIN_ACCESS_COOKIE = "admin_access_token"
ADMIN_REFRESH_COOKIE = "admin_refresh_token"