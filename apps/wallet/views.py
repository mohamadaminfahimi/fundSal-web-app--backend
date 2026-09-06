from __future__ import annotations

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AssetHolding, Wallet
from .serializers import AssetHoldingSerializer, WalletSerializer
from .services import WalletService


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
