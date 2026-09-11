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

# فایل .env فقط در development خوانده می‌شود؛ در production مقادیر باید
# مستقیماً توسط سیستم Orchestration (مثل Docker Compose) تزریق شوند
# تا فایل .env به صورت تصادفی داخل ایمیج Docker یا Git کپی نشود.
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
    "apps.common",
    "apps.users",
    "apps.market",
    "apps.wallet",
    "apps.transactions",
    "apps.invoices",
    "apps.trading",
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
#
# از NUMERIC/DECIMAL برای فیلدهای مالی استفاده می‌شود، نه float.
# این تنظیم در Migration های هر اپ (نه اینجا) اعمال می‌شود، اما موتور دیتابیس
# باید PostgreSQL باشد چون دقت (precision) لازم برای NUMERIC را به درستی
# پشتیبانی می‌کند؛ برخلاف بعضی دیتابیس‌های دیگر که float را جایگزین می‌کنند.
# ---------------------------------------------------------------------------

# config/settings/base.py

DATABASES = {
    "default": {
        **env.db("DATABASE_URL"),
        "CONN_MAX_AGE": 600,  # ✅ اتصال رو ۱۰ دقیقه باز نگه دار
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

# باید همیشه از همان ابتدای پروژه، پیش از اولین migrate، تنظیم شود؛ تغییر
# آن بعد از اجرای Migration های واقعی روی دیتابیس عملاً غیرممکن است.
AUTH_USER_MODEL = "users.User"

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
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
#
# فقط origin های صراحتاً مجاز (فرانت‌اند Next.js) اجازه دسترسی دارند؛
# هرگز از CORS_ALLOW_ALL_ORIGINS=True استفاده نمی‌شود چون در ترکیب با
# CORS_ALLOW_CREDENTIALS=True دسترسی هر وب‌سایتی به Cookie های احراز هویت
# کاربر را ممکن می‌کند (یک آسیب‌پذیری امنیتی جدی).
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Django REST Framework
#
# تنظیم پیش‌فرض Authentication روی JWT (از طریق HttpOnly Cookie) قرار می‌گیرد.
# جزئیات کامل معماری Authentication در Phase 5 پیاده‌سازی می‌شود؛ اینجا فقط
# اسکلت تنظیمات آماده می‌شود تا در فازهای بعدی صرفاً تکمیل شود.
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
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

SPECTACULAR_SETTINGS = {
    "TITLE": "Precious Metals Trading Platform API",
    "DESCRIPTION": "API برای خرید، فروش و مدیریت طلا و نقره.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    # طول عمر کوتاه Access Token ریسک سرقت توکن را کاهش می‌دهد؛ حتی اگر
    # توکن لو برود، مدت اعتبار آن محدود است.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # چرخش (Rotation) خودکار Refresh Token همراه با Blacklist کردن توکن قدیمی
    # از Replay Attack با یک Refresh Token سرقت‌شده جلوگیری می‌کند.
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# Logging
#
# ساختار پایه‌ی Logging؛ جزئیات کامل (فرمت JSON، ارسال به سیستم مانیتورینگ)
# در Phase 15 تکمیل می‌شود.
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




# جایگزین LocMemCache
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "IGNORE_EXCEPTIONS": True,  # اگه Redis خطا داد، کرش نکن
        },
        "KEY_PREFIX": "gold",
        "TIMEOUT": 300,
    }
}