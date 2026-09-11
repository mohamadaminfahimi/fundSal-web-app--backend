# apps/wallet/views.py

from __future__ import annotations

import logging
import time

from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.utils import quantize_money
from apps.market.services import MarketService

from .models import AssetHolding, Wallet
from .serializers import AssetHoldingSerializer, WalletSerializer
from .services import WalletService

logger = logging.getLogger(__name__)


# ============================================================
# Cache TTLs - در یک جا تعریف میشن
# ============================================================

class CacheTTL:
    WALLET = 60        # ۱ دقیقه
    ASSETS = 60        # ۱ دقیقه
    PORTFOLIO = 30     # ۳۰ ثانیه
    DASHBOARD = 30     # ۳۰ ثانیه
    PRICES = 60        # ۱ دقیقه


def cache_key(prefix: str, user_id: int) -> str:
    """ساخت کلید کش به صورت متمرکز"""
    return f"{prefix}:user:{user_id}"


# ============================================================
# Helper Functions
# ============================================================

def get_wallet(user) -> Wallet:
    """گرفتن یا ساختن کیف پول کاربر"""
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


def get_wallet_data(wallet: Wallet) -> dict:
    """تبدیل Wallet به دیکشنری برای پاسخ"""
    return {
        "id": wallet.id,
        "available_balance": str(wallet.available_balance),
        "pending_balance": str(wallet.pending_balance),
        "total_balance": str(wallet.total_balance),
        "currency": wallet.currency,
        "created_at": wallet.created_at.isoformat() if wallet.created_at else None,
        "updated_at": wallet.updated_at.isoformat() if wallet.updated_at else None,
    }


def get_assets_data(user) -> list[dict]:
    """گرفتن دارایی‌های کاربر"""
    holdings = AssetHolding.objects.filter(user=user).only(
        "id", "metal_code", "available_quantity", "locked_quantity",
    )
    return [
        {
            "id": h.id,
            "metal_code": h.metal_code,
            "available_quantity": str(h.available_quantity),
            "locked_quantity": str(h.locked_quantity),
            "total_quantity": str(h.available_quantity + h.locked_quantity),
        }
        for h in holdings
    ]


def get_prices_data() -> list[dict]:
    """گرفتن قیمت‌ها (از کش مشترک)"""
    prices = cache.get("market:prices")
    if prices:
        return prices

    from apps.market.services.price_service import price_service
    prices_raw = price_service.get_prices()
    prices = [
        {
            "metal_code": p["metal_code"],
            "price": str(p["price"]),
            "change_percent": str(p["change_percent"]),
            "updated_at": p["updated_at"],
        }
        for p in prices_raw
    ]
    cache.set("market:prices", prices, CacheTTL.PRICES)
    return prices


def get_portfolio_data(user, wallet: Wallet = None, assets: list = None, prices: list = None) -> dict:
    """محاسبه پورتفولیو"""
    if wallet is None:
        wallet = get_wallet(user)
    if assets is None:
        assets = get_assets_data(user)
    if prices is None:
        prices = get_prices_data()

    prices_map = {p["metal_code"]: p for p in prices}
    total_assets_value = quantize_money(0)

    for asset in assets:
        total_qty = float(asset["total_quantity"])
        price_info = prices_map.get(asset["metal_code"])
        if price_info:
            value = quantize_money(float(price_info["price"]) * total_qty)
            total_assets_value += value
            asset["price_per_gram"] = price_info["price"]
            asset["value"] = str(value)
        else:
            asset["price_per_gram"] = None
            asset["value"] = None

    return {
        "wallet": get_wallet_data(wallet),
        "assets": assets,
        "total_assets_value": str(total_assets_value),
        "portfolio_value": str(
            quantize_money(total_assets_value + wallet.total_balance)
        ),
    }


# ============================================================
# Views
# ============================================================

class WalletView(APIView):
    """GET /api/v1/wallet/ - اطلاعات کیف پول"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start = time.time()
        user_id = request.user.id
        key = cache_key("wallet", user_id)

        cached = cache.get(key)
        if cached:
            duration = (time.time() - start) * 1000
            logger.info(f"⚡ Wallet from CACHE in {duration:.0f}ms")
            return Response({"success": True, "data": cached})

        wallet = get_wallet(request.user)
        data = get_wallet_data(wallet)
        cache.set(key, data, CacheTTL.WALLET)

        duration = (time.time() - start) * 1000
        logger.info(f"💾 Wallet from DB in {duration:.0f}ms")
        return Response({"success": True, "data": data})


class AssetHoldingView(APIView):
    """GET /api/v1/wallet/assets/ - دارایی‌های فلزی"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start = time.time()
        user_id = request.user.id
        key = cache_key("assets", user_id)

        cached = cache.get(key)
        if cached is not None:
            duration = (time.time() - start) * 1000
            logger.info(f"⚡ Assets from CACHE in {duration:.0f}ms")
            return Response({"success": True, "data": cached})

        data = get_assets_data(request.user)
        cache.set(key, data, CacheTTL.ASSETS)

        duration = (time.time() - start) * 1000
        logger.info(f"💾 Assets from DB in {duration:.0f}ms")
        return Response({"success": True, "data": data})


class WalletAdjustView(APIView):
    """POST /api/v1/wallet/adjust/ - تنظیم کیف پول"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        action = request.data.get("action")
        amount = request.data.get("amount")
        user_id = request.user.id

        if action not in ("credit", "debit"):
            return Response(
                {"success": False, "error": {"code": "INVALID_ACTION", "message": "عملیات نامعتبر است."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet = (
            WalletService.credit(request.user, amount, reason="admin_adjustment")
            if action == "credit"
            else WalletService.debit(request.user, amount, reason="admin_adjustment")
        )

        # ✅ پاک کردن همه کش‌های مرتبط
        for prefix in ("wallet", "assets", "portfolio", "dashboard"):
            cache.delete(cache_key(prefix, user_id))

        return Response({"success": True, "data": get_wallet_data(wallet)})


class PortfolioSummaryView(APIView):
    """GET /api/v1/portfolio/summary/ - خلاصه پورتفولیو"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start = time.time()
        user_id = request.user.id
        key = cache_key("portfolio", user_id)

        cached = cache.get(key)
        if cached:
            duration = (time.time() - start) * 1000
            logger.info(f"⚡ Portfolio from CACHE in {duration:.0f}ms")
            return Response({"success": True, "data": cached})

        data = get_portfolio_data(request.user)
        cache.set(key, data, CacheTTL.PORTFOLIO)

        duration = (time.time() - start) * 1000
        logger.info(f"💾 Portfolio from DB in {duration:.0f}ms")
        return Response({"success": True, "data": data})


class DashboardView(APIView):
    """
    GET /api/v1/dashboard/
    
    ✅ Endpoint ترکیبی برای صفحه اصلی - همه چیز در یک درخواست
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start = time.time()
        user = request.user
        user_id = user.id
        key = cache_key("dashboard", user_id)

        # ✅ از کش
        cached = cache.get(key)
        if cached:
            duration = (time.time() - start) * 1000
            logger.info(f"⚡ Dashboard from CACHE in {duration:.0f}ms")
            return Response({"success": True, "data": cached})

        # ✅ از DB — همه چیز با هم
        wallet = get_wallet(user)
        assets = get_assets_data(user)
        prices = get_prices_data()
        portfolio = get_portfolio_data(user, wallet, assets, prices)

        data = {
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": f"{user.first_name} {user.last_name}".strip(),
                "phone_number": user.phone_number,
                "is_email_verified": user.is_email_verified,
            },
            "wallet": portfolio["wallet"],
            "assets": portfolio["assets"],
            "prices": prices,
            "portfolio": {
                "total_assets_value": portfolio["total_assets_value"],
                "portfolio_value": portfolio["portfolio_value"],
            },
        }

        cache.set(key, data, CacheTTL.DASHBOARD)

        duration = (time.time() - start) * 1000
        logger.info(f"💾 Dashboard from DB in {duration:.0f}ms")
        return Response({"success": True, "data": data})
    