# apps/market/services/price_service.py

"""
سرویس قیمت لحظه‌ای فلزات

⚠️ فعلاً از قیمت‌های دیفالت (ثابت) استفاده می‌کند.
🔜 در آینده: اتصال به API خارجی
"""

import logging
from decimal import Decimal
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


# ⚠️ قیمت‌های دیفالت (موقت - بعداً جایگزین می‌شود)
DEFAULT_PRICES = {
    "GOLD": {
        "price": Decimal("3450000"),
        "change_percent": Decimal("0.45"),
    },
    "SILVER": {
        "price": Decimal("485000"),
        "change_percent": Decimal("-0.23"),
    },
}


class PriceServiceError(Exception):
    """خطای سرویس قیمت"""
    pass


class PriceService:
    """
    سرویس قیمت لحظه‌ای
    
    ⚠️ فعلاً: قیمت‌های دیفالت (ثابت) برمی‌گردونه
    🔜 بعداً: از API خارجی می‌خونه
    """
    
    CACHE_KEY = "market:prices"
    CACHE_TIMEOUT = 300  # ۵ دقیقه
    
    def get_prices(self) -> list[dict]:
        """دریافت همه قیمت‌ها"""
        cached = cache.get(self.CACHE_KEY)
        if cached:
            logger.info("✅ Prices from cache")
            return cached
        
        prices = self._get_default_prices()
        cache.set(self.CACHE_KEY, prices, self.CACHE_TIMEOUT)
        logger.info("⚠️ Using DEFAULT prices (temporary)")
        return prices
    
    def get_price(self, metal_code: str) -> dict | None:
        """دریافت قیمت یک فلز خاص"""
        prices = self.get_prices()
        for p in prices:
            if p["metal_code"] == metal_code.upper():
                return p
        return None
    
    def _get_default_prices(self) -> list[dict]:
        """قیمت‌های دیفالت (موقت)"""
        now = timezone.now()
        
        return [
            {
                "metal_code": code,
                "price": data["price"],
                "change_percent": data["change_percent"],
                "updated_at": now.isoformat(),
            }
            for code, data in DEFAULT_PRICES.items()
        ]


# ✅ نمونه‌های singleton
price_service = PriceService()
market_service = PriceService()

# ✅ alias برای سازگاری با کدهای موجود
MarketService = PriceService