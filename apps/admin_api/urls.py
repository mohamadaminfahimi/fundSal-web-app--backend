# apps/admin_api/urls.py

from django.urls import path

from .views import (
    AdminAssetAdjustView,
    AdminDashboardStatsView,
    AdminInvoiceDetailView,
    AdminInvoiceListView,
    AdminLoginView,
    AdminLogoutView,
    AdminOrderDetailView,
    AdminOrderListView,
    AdminPricesView,
    AdminProfileView,
    AdminUserCreateView,
    AdminUserDetailView,
    AdminUserListView,
    AdminUserTransactionsView,
    AdminUserUpdateView,
    AdminWalletAdjustView,
)

urlpatterns = [
    # Auth
    path("auth/login/", AdminLoginView.as_view(), name="admin-login"),
    path("auth/logout/", AdminLogoutView.as_view(), name="admin-logout"),
    path("auth/profile/", AdminProfileView.as_view(), name="admin-profile"),

    # Dashboard
    path("dashboard/stats/", AdminDashboardStatsView.as_view(), name="admin-dashboard-stats"),

    # Invoices
    path("invoices/", AdminInvoiceListView.as_view(), name="admin-invoice-list"),
    path("invoices/<int:invoice_id>/", AdminInvoiceDetailView.as_view(), name="admin-invoice-detail"),

    # Orders
    path("orders/", AdminOrderListView.as_view(), name="admin-order-list"),
    path("orders/<int:order_id>/", AdminOrderDetailView.as_view(), name="admin-order-detail"),

    # Users
    path("users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("users/create/", AdminUserCreateView.as_view(), name="admin-user-create"),
    path("users/<int:user_id>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("users/<int:user_id>/update/", AdminUserUpdateView.as_view(), name="admin-user-update"),
    path("users/<int:user_id>/transactions/", AdminUserTransactionsView.as_view(), name="admin-user-transactions"),
    path("users/<int:user_id>/wallet/adjust/", AdminWalletAdjustView.as_view(), name="admin-wallet-adjust"),
    path("users/<int:user_id>/assets/adjust/", AdminAssetAdjustView.as_view(), name="admin-asset-adjust"),

    # Prices
    path("prices/", AdminPricesView.as_view(), name="admin-prices"),
]