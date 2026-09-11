# apps/common/signals.py

"""
Cache Invalidation Signals

این ماژول به صورت خودکار کش‌های کاربر رو پس از تغییر مدل‌ها پاک می‌کنه.
با این کار، همیشه داده‌های به‌روز نمایش داده میشن و نیازی نیست
در هر view یا service، دستی cache.delete صدا بزنی.

نحوه کار:
    1. در apps.py هر اپ، register_cache_signals صدا زده میشه.
    2. این تابع یه post_save و post_delete signal ثبت می‌کنه.
    3. هر بار که مدل save/delete شد، کش‌های مرتبط پاک میشن.
"""

import logging

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# ============================================================
# Cache Prefixes - همه کلیدهای کش در یک جا
# ============================================================

ALL_CACHE_PREFIXES = (
    "profile",
    "wallet",
    "assets",
    "portfolio",
    "dashboard",
    "transactions",
)


def clear_user_caches(user_id: int, prefixes: tuple = None) -> int:
    """
    پاک کردن کش‌های یک کاربر
    
    Args:
        user_id: شناسه کاربر
        prefixes: لیست prefixها (اگر None باشه، همه پاک میشن)
    
    Returns:
        تعداد کلیدهای پاک شده
    """
    if not user_id:
        return 0
    
    if prefixes is None:
        prefixes = ALL_CACHE_PREFIXES
    
    deleted_count = 0
    for prefix in prefixes:
        key = f"{prefix}:user:{user_id}"
        if cache.get(key) is not None:
            cache.delete(key)
            deleted_count += 1
            logger.debug(f"🗑️ Cleared cache: {key}")
    
    return deleted_count


def register_cache_signals(model, prefixes: tuple, user_id_attr: str = "user_id"):
    """
    ثبت سیگنال برای پاک کردن کش پس از تغییر یا حذف مدل
    
    Args:
        model: کلاس مدل (مثلاً Wallet)
        prefixes: prefixهای کش که باید پاک بشن
        user_id_attr: نام فیلد در مدل که user_id داره
    
    Usage:
        register_cache_signals(Wallet, ("wallet", "portfolio", "dashboard"))
    """
    model_name = model.__name__
    
    @receiver(
        post_save,
        sender=model,
        dispatch_uid=f"{model_name}_post_save_clear_cache",
        weak=False,
    )
    def on_save(sender, instance, **kwargs):
        user_id = getattr(instance, user_id_attr, None)
        if user_id:
            clear_user_caches(user_id, prefixes)
    
    @receiver(
        post_delete,
        sender=model,
        dispatch_uid=f"{model_name}_post_delete_clear_cache",
        weak=False,
    )
    def on_delete(sender, instance, **kwargs):
        user_id = getattr(instance, user_id_attr, None)
        if user_id:
            clear_user_caches(user_id, prefixes)
    
    logger.info(f"✅ Cache signals registered for {model_name} → {prefixes}")