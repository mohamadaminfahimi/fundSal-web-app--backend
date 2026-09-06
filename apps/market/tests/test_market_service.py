from decimal import Decimal

import pytest

from apps.market.models import PreciousMetal
from apps.market.services import MarketService

pytestmark = pytest.mark.django_db


class TestMarketService:
    def test_upsert_price_creates_price_and_history(self):
        ticker = "XAU"
        MarketService.upsert_price(ticker, Decimal("1200.50"), source="internal")

        assert PreciousMetal.objects.filter(code=ticker).exists()
        assert MarketService.get_latest_price(ticker).price_per_gram == Decimal("1200.50")
