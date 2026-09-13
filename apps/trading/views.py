# apps/trading/views.py

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from django.core.cache import cache
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.views import CustomResponse
from apps.wallet.models import AssetHolding, Wallet
from apps.market.services import MarketService
from .models import Order
from .serializers import OrderSerializer, CreateOrderSerializer

logger = logging.getLogger(__name__)


# ============================================================
# List Orders
# ============================================================

class OrderListView(APIView):
    """GET /api/v1/trading/orders/ - لیست سفارش‌ها"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            orders = Order.objects.filter(user=request.user).order_by("-created_at")
            
            # ✅ فیلتر بر اساس وضعیت (اختیاری)
            order_status = request.query_params.get("status")
            if order_status:
                orders = orders.filter(status=order_status)
            
            # ✅ فیلتر بر اساس طرف (خرید/فروش)
            side = request.query_params.get("side")
            if side:
                orders = orders.filter(side=side)
            
            serializer = OrderSerializer(orders, many=True)
            return CustomResponse.success(data=serializer.data)
        
        except Exception as e:
            logger.exception(f"❌ Error in OrderListView: {e}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================
# Create Buy Order
# ============================================================

class BuyOrderView(APIView):
    """POST /api/v1/trading/orders/buy/"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            from apps.transactions.models import Transaction

            serializer = CreateOrderSerializer(
                data=request.data,
                context={"request": request},
            )

            if not serializer.is_valid():
                return CustomResponse.validation_errors(serializer.errors)

            metal_code = serializer.validated_data["metal_code"]
            quantity = serializer.validated_data["quantity"]
            price_per_gram = serializer.validated_data["price_per_gram"]

            total_amount = quantity * price_per_gram

            # چک موجودی
            try:
                wallet = Wallet.objects.select_for_update().get(user=request.user)
            except Wallet.DoesNotExist:
                wallet = Wallet.objects.create(user=request.user)

            if wallet.available_balance < total_amount:
                return CustomResponse.error(
                    code="INP_002",
                    detail=f"موجودی کیف پول کافی نیست. موجودی شما: {wallet.available_balance:,.0f} تومان",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            # کسر از کیف پول
            wallet.available_balance -= total_amount
            wallet.save()

            # ساخت سفارش
            order = Order.objects.create(
                user=request.user,
                metal_code=metal_code,
                side="buy",
                order_type="market",
                quantity=quantity,
                remaining_quantity=quantity,
                price_per_gram=price_per_gram,
                total_amount=total_amount,
                idempotency_key=str(uuid.uuid4()),
                status="pending",
                metadata={
                    "price_per_gram": str(price_per_gram),
                    "total_amount": str(total_amount),
                    "quantity": str(quantity),
                    "metal_code": metal_code,
                },
            )

            # ✅ ثبت تراکنش
            Transaction.objects.create(
                user=request.user,
                transaction_type="buy_order",
                amount=total_amount,
                currency="IRR",
                status="pending",
                reference_id=f"buy-order-{order.id}",
                metadata={
                    "order_id": order.id,
                    "metal_code": metal_code,
                    "quantity": str(quantity),
                    "price_per_gram": str(price_per_gram),
                    "total_amount": str(total_amount),
                    "side": "buy",
                },
            )

            # پاک کردن کش
            cache.delete(f"wallet:user:{request.user.id}")
            cache.delete(f"dashboard:user:{request.user.id}")
            cache.delete(f"transactions:user:{request.user.id}")

            logger.info(
                f"✅ Buy order created: {order.id} - "
                f"{quantity} {metal_code} by {request.user.email}"
            )

            return CustomResponse.success(
                data=OrderSerializer(order).data,
                message=f"سفارش خرید {quantity} گرم {metal_code} با موفقیت ثبت شد.",
                status_code=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.exception(f"❌ Error in BuyOrderView: {e}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



                
# ============================================================
# Create Sell Order
# ============================================================

class SellOrderView(APIView):
    """POST /api/v1/trading/orders/sell/"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            from apps.transactions.models import Transaction

            serializer = CreateOrderSerializer(
                data=request.data,
                context={"request": request},
            )

            if not serializer.is_valid():
                return CustomResponse.validation_errors(serializer.errors)

            metal_code = serializer.validated_data["metal_code"]
            quantity = serializer.validated_data["quantity"]
            price_per_gram = serializer.validated_data["price_per_gram"]

            total_amount = quantity * price_per_gram

            # چک دارایی
            try:
                holding = AssetHolding.objects.select_for_update().get(
                    user=request.user,
                    metal_code=metal_code,
                )
            except AssetHolding.DoesNotExist:
                return CustomResponse.error(
                    code="INP_002",
                    detail=f"شما {metal_code} ندارید.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            if holding.available_quantity < quantity:
                return CustomResponse.error(
                    code="INP_002",
                    detail=f"موجودی {metal_code} کافی نیست. موجودی شما: {holding.available_quantity} گرم",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            holding.available_quantity -= quantity
            holding.save()

            try:
                wallet = Wallet.objects.select_for_update().get(user=request.user)
            except Wallet.DoesNotExist:
                wallet = Wallet.objects.create(user=request.user)

            wallet.pending_balance += total_amount
            wallet.save()

            order = Order.objects.create(
                user=request.user,
                metal_code=metal_code,
                side="sell",
                order_type="market",
                quantity=quantity,
                remaining_quantity=quantity,
                price_per_gram=price_per_gram,
                total_amount=total_amount,
                idempotency_key=str(uuid.uuid4()),
                status="pending",
                metadata={
                    "price_per_gram": str(price_per_gram),
                    "total_amount": str(total_amount),
                    "quantity": str(quantity),
                    "metal_code": metal_code,
                },
            )

            # ✅ ثبت تراکنش
            Transaction.objects.create(
                user=request.user,
                transaction_type="sell_order",
                amount=total_amount,
                currency="IRR",
                status="pending",
                reference_id=f"sell-order-{order.id}",
                metadata={
                    "order_id": order.id,
                    "metal_code": metal_code,
                    "quantity": str(quantity),
                    "price_per_gram": str(price_per_gram),
                    "total_amount": str(total_amount),
                    "side": "sell",
                },
            )

            cache.delete(f"wallet:user:{request.user.id}")
            cache.delete(f"assets:user:{request.user.id}")
            cache.delete(f"dashboard:user:{request.user.id}")
            cache.delete(f"transactions:user:{request.user.id}")

            logger.info(
                f"✅ Sell order created: {order.id} - "
                f"{quantity} {metal_code} by {request.user.email}"
            )

            return CustomResponse.success(
                data=OrderSerializer(order).data,
                message=f"سفارش فروش {quantity} گرم {metal_code} با موفقیت ثبت شد.",
                status_code=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.exception(f"❌ Error in SellOrderView: {e}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
