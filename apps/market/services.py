from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from apps.common.utils import quantize_money
from apps.market.models import MarketPrice, PriceHistory, PreciousMetal


class MarketService:
    """خدمات بازار؛ قیمت‌ها به‌صورت غیرقابل‌اعتماد از Provider جدا می‌شوند و در دیتابیس استاندارد می‌شوند."""

    @staticmethod
    def upsert_price(metal_code: str, price_per_gram: Decimal | str, source: str = "internal_provider") -> MarketPrice:
        metal, _ = PreciousMetal.objects.get_or_create(code=metal_code, defaults={"name": metal_code.upper()})
        price_value = quantize_money(price_per_gram)
        now = timezone.now()
        market_price, _ = MarketPrice.objects.get_or_create(
            metal=metal,
            defaults={"price_per_gram": price_value, "source": source, "valid_from": now},
        )
        market_price.price_per_gram = price_value
        market_price.source = source
        market_price.valid_from = now
        market_price.valid_until = None
        market_price.save(update_fields=["price_per_gram", "source", "valid_from", "valid_until", "updated_at"])
        PriceHistory.objects.create(metal=metal, price_per_gram=price_value)
        return market_price

    @staticmethod
    def get_latest_price(metal_code: str):
        return MarketPrice.objects.filter(metal__code=metal_code).order_by("-valid_from").first()
