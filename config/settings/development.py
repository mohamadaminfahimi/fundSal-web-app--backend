"""
تنظیمات مخصوص محیط توسعه (development).

اجرا با:
    DJANGO_SETTINGS_MODULE=config.settings.development
"""

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS += ["django_extensions"]  # noqa: F405

# در development نیازی به اجبار HTTPS نیست؛ این باعث ساده‌تر شدن تست محلی
# می‌شود بدون این‌که امنیت production را تحت تأثیر قرار دهد.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

LOGGING["root"]["level"] = "DEBUG"  # noqa: F405
