"""Version 1 endpoint registry.

Views and business logic stay in their domain apps; this module owns the
public API paths and keeps the API surface in one place.
"""

from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import health_check
from apps.trading.views import BuyOrderView, OrderListView, SellOrderView
from apps.transactions.views import TransactionDetailView, TransactionListView
from apps.users.views import LoginView, LogoutView, ProfileView, RefreshTokenView, RegisterView
from apps.wallet.views import AssetHoldingView, WalletAdjustView, WalletView
from apps.wallet.views import PortfolioSummaryView
from apps.market.views import MarketPricesView

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/refresh/", RefreshTokenView.as_view(), name="refresh-token"),
    path("auth/profile/", ProfileView.as_view(), name="profile"),
    path("wallet/", WalletView.as_view(), name="wallet-detail"),
    path("wallet/assets/", AssetHoldingView.as_view(), name="wallet-assets"),
    path("wallet/adjust/", WalletAdjustView.as_view(), name="wallet-adjust"),
    path("transactions/", TransactionListView.as_view(), name="transaction-list"),
    path(
        "transactions/<int:transaction_id>/",
        TransactionDetailView.as_view(),
        name="transaction-detail",
    ),
    path("trading/orders/", OrderListView.as_view(), name="trading-order-list"),
    path("trading/orders/buy/", BuyOrderView.as_view(), name="trading-buy-order"),
    path("trading/orders/sell/", SellOrderView.as_view(), name="trading-sell-order"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("market/prices", MarketPricesView.as_view(), name="market-prices"),
    path("portfolio/summary", PortfolioSummaryView.as_view(), name="portfolio-summary"),
]
