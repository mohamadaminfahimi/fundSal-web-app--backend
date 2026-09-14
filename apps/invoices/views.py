# apps/invoices/views.py

from __future__ import annotations

import logging

from django.core.cache import cache
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.signals import clear_user_caches
from apps.users.views import CustomResponse
from apps.wallet.models import Wallet

from .models import Invoice
from .serializers import CreateInvoiceSerializer, InvoiceSerializer

logger = logging.getLogger(__name__)


# ============================================================
# List Invoices
# ============================================================

class InvoiceListView(APIView):
    """GET /api/v1/invoices/ - لیست فاکتورهای کاربر"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            qs = Invoice.objects.filter(user=request.user).order_by("-created_at")
            serializer = InvoiceSerializer(qs, many=True)
            return CustomResponse.success(data=serializer.data)
        except Exception as e:
            logger.exception(f"❌ Error in InvoiceListView: {e}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================
# Create Invoice
# ============================================================

class CreateInvoiceView(APIView):
    """POST /api/v1/invoices/create/ - ساخت فاکتور واریز/برداشت"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            serializer = CreateInvoiceSerializer(
                data=request.data,
                context={"request": request},
            )

            if not serializer.is_valid():
                return CustomResponse.validation_errors(serializer.errors)

            data = serializer.validated_data
            transaction_type = data["transaction_type"]
            amount = data["amount"]

            # ============================================================
            # ✅ اگر برداشت است، همزمان از available کم کن
            # ============================================================
            if transaction_type == "withdraw":
                try:
                    wallet = Wallet.objects.select_for_update().get(user=request.user)
                except Wallet.DoesNotExist:
                    wallet = Wallet.objects.create(user=request.user)

                if wallet.available_balance < amount:
                    return CustomResponse.error(
                        code="INP_002",
                        detail=f"موجودی کافی نیست. موجودی شما: {wallet.available_balance:,.0f} تومان",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

                # ✅ فقط از available کم کن
                wallet.available_balance -= amount
                wallet.save()

                logger.info(
                    f"✅ Withdraw request: {amount} from user {request.user.id}. "
                    f"new available: {wallet.available_balance}"
                )

            # ============================================================
            # ساخت فاکتور
            # ============================================================
            invoice = serializer.save()

            # ✅ پاک کردن کامل کش‌های کاربر
            clear_user_caches(request.user.id)

            logger.info(
                f"✅ Invoice created: {invoice.number} - {transaction_type} - {amount}"
            )

            return CustomResponse.success(
                data=InvoiceSerializer(invoice).data,
                message="درخواست با موفقیت ثبت شد.",
                status_code=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.exception(f"❌ Error in CreateInvoiceView: {e}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================
# Invoice Detail
# ============================================================

class InvoiceDetailView(APIView):
    """GET /api/v1/invoices/{id}/ - جزئیات یک فاکتور"""
    permission_classes = [IsAuthenticated]

    def get(self, request, invoice_id):
        try:
            invoice = Invoice.objects.filter(
                user=request.user, id=invoice_id
            ).first()

            if invoice is None:
                return CustomResponse.error(
                    code="GEN_002",
                    detail="فاکتور یافت نشد.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CustomResponse.success(data=InvoiceSerializer(invoice).data)

        except Exception as e:
            logger.exception(f"❌ Error in InvoiceDetailView: {e}")
            return CustomResponse.error(
                code="GEN_001",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )