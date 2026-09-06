from django.urls import path

from .views import BuyOrderView, OrderListView, SellOrderView

urlpatterns = [
    path("orders/", OrderListView.as_view(), name="trading-order-list"),
    path("orders/buy/", BuyOrderView.as_view(), name="trading-buy-order"),
    path("orders/sell/", SellOrderView.as_view(), name="trading-sell-order"),
]
