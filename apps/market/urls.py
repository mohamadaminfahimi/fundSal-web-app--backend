# apps/market/urls.py

from django.urls import path
from .views import MarketPricesView

urlpatterns = [
    path("prices/", MarketPricesView.as_view(), name="market-prices"),
]