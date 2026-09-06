from django.urls import path

from .views import AssetHoldingView, WalletAdjustView, WalletView

urlpatterns = [
    path("wallet/", WalletView.as_view(), name="wallet-detail"),
    path("wallet/assets/", AssetHoldingView.as_view(), name="wallet-assets"),
    path("wallet/adjust/", WalletAdjustView.as_view(), name="wallet-adjust"),
]
