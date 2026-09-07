from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.market.models import PreciousMetal
from apps.market.services import MarketService


class MarketPricesView(APIView):
    """Return latest market prices for active precious metals.

    GET /api/v1/market/prices
    """

    permission_classes = []

    def get(self, request):
        metals = PreciousMetal.objects.filter(is_active=True).order_by("code")
        data = []
        for m in metals:
            latest = MarketService.get_latest_price(m.code)
            if latest:
                data.append(
                    {
                        "code": m.code,
                        "name": m.name,
                        "unit": m.unit,
                        "price_per_gram": str(latest.price_per_gram),
                        "source": latest.source,
                        "valid_from": latest.valid_from.isoformat() if latest.valid_from else None,
                    }
                )
            else:
                data.append({"code": m.code, "name": m.name, "unit": m.unit, "price_per_gram": None})

        return Response(data, status=status.HTTP_200_OK)
