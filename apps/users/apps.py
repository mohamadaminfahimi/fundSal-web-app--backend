# apps/users/apps.py

from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    verbose_name = "Users"

    def ready(self):
        # ✅ ثبت سیگنال برای User
        from django.contrib.auth import get_user_model
        from apps.common.signals import register_cache_signals
        
        User = get_user_model()
        register_cache_signals(
            User,
            prefixes=("profile", "dashboard"),
        )