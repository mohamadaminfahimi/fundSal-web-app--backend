"""Version 1 endpoint registry."""

from django.conf.urls import include
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import health_check
from apps.invoices.views import (
    CreateInvoiceView,
    InvoiceDetailView,
    InvoiceListView,
)
from apps.market.views import MarketPricesView
from apps.trading.views import BuyOrderView, OrderListView, SellOrderView
from apps.transactions.views import TransactionDetailView, TransactionListView
from apps.users.views import LoginView, LogoutView, ProfileView, RefreshTokenView, RegisterView
from apps.wallet.views import (
    AssetHoldingView,
    DashboardView,
    PortfolioSummaryView,
    WalletAdjustView,
    WalletView,
)

urlpatterns = [
    # -----------------------------------------------------------------------
    # Health
    # -----------------------------------------------------------------------
    path("health/", health_check, name="health-check"),

    # -----------------------------------------------------------------------
    # Auth
    # -----------------------------------------------------------------------
    path("auth/", include("apps.users.urls")),  # ✅ همه auth از این می‌آید

    # -----------------------------------------------------------------------
    # Dashboard (ترکیبی)
    # -----------------------------------------------------------------------
    path("dashboard/", DashboardView.as_view(), name="dashboard"),

    # -----------------------------------------------------------------------
    # Wallet
    # -----------------------------------------------------------------------
    path("wallet/", WalletView.as_view(), name="wallet-detail"),
    path("wallet/assets/", AssetHoldingView.as_view(), name="wallet-assets"),
    path("wallet/adjust/", WalletAdjustView.as_view(), name="wallet-adjust"),

    # -----------------------------------------------------------------------
    # Portfolio
    # -----------------------------------------------------------------------
    path("portfolio/summary/", PortfolioSummaryView.as_view(), name="portfolio-summary"),

    # -----------------------------------------------------------------------
    # Invoices (فاکتورها - واریز/برداشت/خرید/فروش)
    # -----------------------------------------------------------------------
    path("invoices/", InvoiceListView.as_view(), name="invoice-list"),
    path("invoices/create/", CreateInvoiceView.as_view(), name="invoice-create"),
    path(
        "invoices/<int:invoice_id>/",
        InvoiceDetailView.as_view(),
        name="invoice-detail",
    ),

    # -----------------------------------------------------------------------
    # Transactions
    # -----------------------------------------------------------------------
    path("transactions/", TransactionListView.as_view(), name="transaction-list"),
    path(
        "transactions/<int:transaction_id>/",
        TransactionDetailView.as_view(),
        name="transaction-detail",
    ),

    # -----------------------------------------------------------------------
    # Trading
    # -----------------------------------------------------------------------
    path("trading/orders/", OrderListView.as_view(), name="trading-order-list"),
    path("trading/orders/buy/", BuyOrderView.as_view(), name="trading-buy-order"),
    path("trading/orders/sell/", SellOrderView.as_view(), name="trading-sell-order"),

    # -----------------------------------------------------------------------
    # Market
    # -----------------------------------------------------------------------
    path("market/prices/", MarketPricesView.as_view(), name="market-prices"),

    # -----------------------------------------------------------------------
    # Docs
    # -----------------------------------------------------------------------
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

        # ✅ Admin API
    path("admin/", include("apps.admin_api.urls")),


]