# apps/transactions/apps.py

from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.transactions"
    verbose_name = "Transactions"

    def ready(self):
        # ✅ ثبت سیگنال برای Transaction (اگر user_id داره)
        from apps.common.signals import register_cache_signals
        
        # اگه مدل Transaction داری و user_id داره:
        # from .models import Transaction
        # register_cache_signals(
        #     Transaction,
        #     prefixes=("transactions", "dashboard"),
        # )
        pass