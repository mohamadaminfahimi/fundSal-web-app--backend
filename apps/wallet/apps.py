# apps/wallet/apps.py

from django.apps import AppConfig


class WalletConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.wallet"
    verbose_name = "Wallet"

    def ready(self):
        # ✅ ثبت سیگنال برای پاک کردن خودکار کش
        # این خط بعد از لود شدن همه مدل‌ها اجرا میشه
        from apps.common.signals import register_cache_signals
        from .models import AssetHolding, Wallet
        
        register_cache_signals(
            Wallet,
            prefixes=("wallet", "portfolio", "dashboard"),
        )
        
        register_cache_signals(
            AssetHolding,
            prefixes=("assets", "portfolio", "dashboard"),
        )