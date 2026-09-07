from __future__ import annotations

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AssetHolding, Wallet
from .serializers import AssetHoldingSerializer, WalletSerializer
from .services import WalletService
from apps.market.services import MarketService
from apps.common.utils import quantize_money, quantize_weight


class WalletView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)
        return Response({"success": True, "data": serializer.data})


class AssetHoldingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        holdings = AssetHolding.objects.filter(user=request.user)
        serializer = AssetHoldingSerializer(holdings, many=True)
        return Response({"success": True, "data": serializer.data})


class WalletAdjustView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        action = request.data.get("action")
        amount = request.data.get("amount")

        if action == "credit":
            wallet = WalletService.credit(request.user, amount, reason="admin_adjustment")
            return Response({"success": True, "data": WalletSerializer(wallet).data}, status=status.HTTP_200_OK)

        if action == "debit":
            wallet = WalletService.debit(request.user, amount, reason="admin_adjustment")
            return Response({"success": True, "data": WalletSerializer(wallet).data}, status=status.HTTP_200_OK)

        return Response({"success": False, "error": {"code": "INVALID_ACTION", "message": "عملیات نامعتبر است."}}, status=status.HTTP_400_BAD_REQUEST)


class PortfolioSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        holdings = AssetHolding.objects.filter(user=request.user)

        assets = []
        total_assets_value = quantize_money(0)

        for h in holdings:
            total_qty = h.total_quantity
            latest = MarketService.get_latest_price(h.metal_code)
            price = latest.price_per_gram if latest else None
            if price is not None:
                value = quantize_money(price * total_qty)
                total_assets_value += value
            else:
                value = None

            assets.append(
                {
                    "metal_code": h.metal_code,
                    "available_quantity": str(h.available_quantity),
                    "locked_quantity": str(h.locked_quantity),
                    "total_quantity": str(total_qty),
                    "price_per_gram": str(price) if price is not None else None,
                    "value": str(value) if value is not None else None,
                }
            )

        summary = {
            "wallet": {
                "available_balance": str(wallet.available_balance),
                "pending_balance": str(wallet.pending_balance),
                "total_balance": str(wallet.total_balance),
                "currency": wallet.currency,
            },
            "assets": assets,
            "total_assets_value": str(total_assets_value),
            "portfolio_value": str(quantize_money(total_assets_value + wallet.total_balance)),
        }

        return Response({"success": True, "data": summary}, status=status.HTTP_200_OK)
