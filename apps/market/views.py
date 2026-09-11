# apps/market/views.py

import logging
import time

from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services.price_service import price_service, PriceServiceError

logger = logging.getLogger(__name__)

CACHE_TTL_PRICES = 60  # ۱ دقیقه


class MarketPricesView(APIView):
    """GET /api/v1/market/prices/ - قیمت لحظه‌ای فلزات"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start = time.time()
        cache_key = "market:prices"

        # ✅ از کش
        cached = cache.get(cache_key)
        if cached is not None:
            duration = (time.time() - start) * 1000
            logger.info(f"⚡ Prices from CACHE in {duration:.0f}ms")
            return Response({
                "success": True,
                "data": cached,
                "source": "cache",
            })

        try:
            prices = price_service.get_prices()
            data = [
                {
                    "metal_code": p["metal_code"],
                    "price": str(p["price"]),
                    "change_percent": str(p["change_percent"]),
                    "updated_at": p["updated_at"],
                }
                for p in prices
            ]

            # ✅ ذخیره در کش
            cache.set(cache_key, data, CACHE_TTL_PRICES)

            duration = (time.time() - start) * 1000
            logger.info(f"💾 Prices from SERVICE in {duration:.0f}ms")

            return Response({
                "success": True,
                "data": data,
                "source": "default",
            })

        except PriceServiceError as e:
            logger.error(f"❌ Price service error: {e}")
            return Response(
                {
                    "success": False,
                    "error": {"code": "PRICE_UNAVAILABLE", "message": str(e)},
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception as e:
            logger.exception(f"❌ Unexpected error: {e}")
            return Response(
                {
                    "success": False,
                    "error": {"code": "INTERNAL_ERROR", "message": "خطای داخلی سرور"},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )