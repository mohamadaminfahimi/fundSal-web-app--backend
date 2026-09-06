from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.trading.models import Order
from apps.trading.serializers import OrderSerializer
from apps.trading.services import TradingService


class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        orders = Order.objects.filter(user=request.user).order_by("-created_at")
        serializer = OrderSerializer(orders, many=True)
        return Response({"success": True, "data": serializer.data})


class BuyOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            order = TradingService.create_buy_order(
                request.user,
                data.get("metal_code"),
                data.get("quantity"),
                data.get("price_per_gram"),
                data.get("idempotency_key", ""),
            )
            return Response({"success": True, "data": OrderSerializer(order).data}, status=status.HTTP_201_CREATED)
        except ValueError as exc:
            message = str(exc)
            code = "INVALID_REQUEST"
            if message == "INSUFFICIENT_BALANCE":
                code = "INSUFFICIENT_BALANCE"
            elif message == "IDEMPOTENCY_KEY_REQUIRED":
                code = "IDEMPOTENCY_KEY_REQUIRED"
            return Response({"success": False, "error": {"code": code, "message": message}}, status=status.HTTP_400_BAD_REQUEST)


class SellOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            order = TradingService.create_sell_order(
                request.user,
                data.get("metal_code"),
                data.get("quantity"),
                data.get("price_per_gram"),
                data.get("idempotency_key", ""),
            )
            return Response({"success": True, "data": OrderSerializer(order).data}, status=status.HTTP_201_CREATED)
        except ValueError as exc:
            message = str(exc)
            code = "INVALID_REQUEST"
            if message == "INSUFFICIENT_ASSET":
                code = "INSUFFICIENT_ASSET"
            elif message == "IDEMPOTENCY_KEY_REQUIRED":
                code = "IDEMPOTENCY_KEY_REQUIRED"
            return Response({"success": False, "error": {"code": code, "message": message}}, status=status.HTTP_400_BAD_REQUEST)
