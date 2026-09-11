# apps/trading/apps.py

from django.apps import AppConfig


class TradingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.trading"
    verbose_name = "Trading"

    def ready(self):
        # ✅ ثبت سیگنال برای Order (اگر user_id داره)
        from apps.common.signals import register_cache_signals
        
        # اگه مدل Order داری و user_id داره:
        # from .models import Order
        # register_cache_signals(
        #     Order,
        #     prefixes=("dashboard",),
        # )
        pass